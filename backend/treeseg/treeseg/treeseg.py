import heapq

import numpy as np
from services.embedding_service import EmbeddingModel
from loguru import logger


class SegNode:
    def __init__(self, identifier, entries, configs):
        self.configs = configs
        self.MIN_SEGMENT_SIZE = configs["MIN_SEGMENT_SIZE"]
        self.MAX_SEGMENT_SIZE = configs.get("MAX_SEGMENT_SIZE", 100)
        self.LAMBDA_BALANCE = configs["LAMBDA_BALANCE"]
        self.entries = entries
        self.segment = [entry["index"] for entry in entries]
        self.embs = [entry["embedding"] for entry in entries]
        self.embs = np.array(self.embs)
        self.mu = np.mean(self.embs, axis=0)

        self.left = None
        self.right = None

        self.identifier = identifier

        self.is_leaf = (
            len(entries) < 2 * self.MIN_SEGMENT_SIZE
            or len(entries) <= self.MAX_SEGMENT_SIZE
        )

        if self.is_leaf:
            return

        self.compute_likelihood()
        self.optimize_split()

    def squared_error(self, X, mu):
        return np.sum(np.sum(np.square(X - mu), axis=-1))

    def compute_likelihood(self):
        self.mu = np.mean(self.embs, axis=0, keepdims=True)
        self.negative_log_likelihood = self.squared_error(self.embs, self.mu)
        self.negative_log_likelihood += self.LAMBDA_BALANCE * np.square(
            len(self.entries)
        )

    def optimize_split(self):
        N = len(self.entries)
        index = list(np.arange(N))

        min_loss = float("inf")

        losses = []

        S0 = None
        S1 = None

        for n in range(self.MIN_SEGMENT_SIZE - 1, N - self.MIN_SEGMENT_SIZE):
            if S0 is None:
                idx0 = index[: n + 1]
                idx1 = index[n + 1 :]

                X0 = self.embs[idx0]
                X1 = self.embs[idx1]

                S0 = np.sum(X0, axis=0)
                SS0 = np.sum(np.square(X0), axis=0)

                S1 = np.sum(X1, axis=0)
                SS1 = np.sum(np.square(X1), axis=0)

                M0 = len(idx0)
                M1 = len(idx1)
            else:
                M0 += 1
                M1 -= 1

                v = self.embs[n]

                S0 += v
                S1 -= v

                SS0 += np.square(v)
                SS1 -= np.square(v)

            assert M0 + M1 == N

            mu0 = S0 / M0
            mu1 = S1 / M1

            loss = np.sum(SS0 - np.square(mu0) * M0)
            loss += np.sum(SS1 - np.square(mu1) * M1)

            balance_penalty = self.LAMBDA_BALANCE * np.square(M0)
            balance_penalty += self.LAMBDA_BALANCE * np.square(M1)
            loss += balance_penalty

            losses.append(loss)

            if loss < min_loss:
                min_loss = loss
                self.split_negative_log_likelihood = loss
                self.split_entries = [self.entries[: n + 1], self.entries[n + 1 :]]

    def split_loss_delta(self):
        return self.split_negative_log_likelihood - self.negative_log_likelihood

    def split(self):
        left_entries, right_entries = self.split_entries

        self.left = SegNode(
            identifier=self.identifier + "L",
            entries=left_entries,
            configs=self.configs,
        )
        self.right = SegNode(
            identifier=self.identifier + "R",
            entries=right_entries,
            configs=self.configs,
        )
        return self.left, self.right


class TreeSeg:
    def __init__(self, configs, entries, async_embedding_model: EmbeddingModel):
        self.configs = configs
        self.entries = entries
        self.async_embedding_model = async_embedding_model
        self.extract_blocks()
        self.blocks = [block for block in self.blocks if block["convo"].strip()]

        for i, block in enumerate(self.blocks):
            block["index"] = i

    def discover_leaves(self, cond_func=lambda x: True, K=float("inf")):
        leaves = []
        stack = [self.root]

        while stack:
            node = stack.pop(0)

            if node.left is None and node.right is None:
                if cond_func(node):
                    leaves.append(node)
                    print(node.identifier, node.segment)

                    if len(leaves) == K:
                        return leaves
                continue

            if node.right:
                stack = [node.right] + stack
            if node.left:
                stack = [node.left] + stack

        return leaves

    async def embed_blocks(self):
        print("Submitting blocks to Cohere API")
        N = len(self.blocks)
        BATCH_SIZE = 96
        num_batches = np.int32(np.ceil(N / BATCH_SIZE))

        print(f"Extracting {N} embeddings in {num_batches} batches.")

        batches = []
        for batch_i in range(num_batches):
            batch = self.blocks[batch_i * BATCH_SIZE : (batch_i + 1) * BATCH_SIZE]
            batches.append(batch)

        embs = []

        for i, batch in enumerate(batches):
            chunk_texts = [block["convo"] for block in batch if block["convo"].strip()]
            if not chunk_texts:
                logger.info("Skipping empty batch...")
                continue

            logger.info(
                f"Processing batch {i+1}/{len(batches)} with {len(chunk_texts)} non-empty texts"
            )
            result = await self.async_embedding_model.async_embed(
                chunk_texts, input_type="search_document", model_id="embed-english-v3.0"
            )

            batch_embs = result.embeddings
            print(f"Received {len(batch_embs)} embeddings from API for batch {i+1}")
            embs.extend(batch_embs)

        print(f"I have collected {len(embs)}/{N} embeddings.")

        if len(embs) != N:
            print(
                f"Warning: Number of embeddings ({len(embs)}) does not match number of blocks ({N})"
            )

        for i, (block, emb) in enumerate(zip(self.blocks, embs)):
            if i < len(embs):
                block["embedding"] = emb
            else:
                print(f"Warning: No embedding for block {i}")

        print(
            f"Embedded {sum(1 for block in self.blocks if 'embedding' in block)}/{N} blocks"
        )

    def extract_blocks(self):
        entries = self.entries
        blocks = []

        width = self.configs["UTTERANCE_EXPANSION_WIDTH"]

        for i, entry in enumerate(entries):
            convo = []
            for idx in range(max(0, i - width), i + 1):
                convo.append(entries[idx]["composite"])
            block = {"convo": "\n".join(convo), "index": i}
            block.update(entry)
            if block["convo"].strip():
                blocks.append(block)

        for i, block in enumerate(blocks):
            block["index"] = i

        self.blocks = blocks

    async def segment_meeting(self, K):
        # First ensure blocks are embedded
        await self.embed_blocks()

        # Now create root node after embeddings are generated
        self.root = SegNode(identifier="*", entries=self.blocks, configs=self.configs)
        root = self.root

        if root.is_leaf:
            print("Cannot split root further. Nothing to do here.")
            return

        leaves = []
        boundary = []
        heapq.heappush(boundary, (root.split_loss_delta(), root))

        loss = root.negative_log_likelihood

        while boundary:
            if len(boundary) + len(leaves) == K:
                print(f"Reached maximum of {K} segments.")
                while boundary:
                    loss_delta, node = heapq.heappop(boundary)
                    node.is_leaf = True
                    heapq.heappush(leaves, (node.segment[0], node))
                break
            loss_delta, node = heapq.heappop(boundary)
            loss += loss_delta

            perc = -loss_delta / loss
            print(f"Loss reduction: {loss-loss_delta}=>{loss} | {100*perc}%")
            left, right = node.split()

            if left.is_leaf:
                heapq.heappush(leaves, (left.segment[0], left))
            else:
                heapq.heappush(boundary, (left.split_loss_delta(), left))

            if right.is_leaf:
                heapq.heappush(leaves, (right.segment[0], right))
            else:
                heapq.heappush(boundary, (right.split_loss_delta(), right))

        sorted_leaves = []
        while leaves:
            sorted_leaves.append(heapq.heappop(leaves)[1])

        self.leaves = sorted_leaves

        transitions_hat = [
            0,
        ] * len(self.leaves[0].segment)

        for leaf in self.leaves[1:]:
            segment_transition = [
                0,
            ] * len(leaf.segment)
            segment_transition[0] = 1
            transitions_hat.extend(segment_transition)

        self.transitions_hat = transitions_hat
        return transitions_hat
