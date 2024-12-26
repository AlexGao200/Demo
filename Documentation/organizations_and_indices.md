# Organizations

## About Organizations

Organizations
- Exist to simplify documents and payments at scale
- Have a role system of admins, editors, and members

## About Indices

Indices
- Contain documents
- Can be personal or belong to an organization
- Currently, each user has exactly one personal index, and each organization has exactly one organizational index.

Organizations can choose document visibility, `private` or `public`, for each document in their index.

User indices can only contain private documents.

## Public vs. Private Documents

Public documents—
- Availability: Public documents are available sitewide for all users.
- Payment: User’s billing organization pays for all query tokens (not the organization of the document being queried).

Private documents—
- Availability: Private documents are available only for an organization's members .
- Payment: the organization of the document pays for all query tokens.

## Organizations & Uploads:
Access: Editors and admins of an organization have free access to create/modify/delete private/public documents for their organization.

### Petitions
Members of any org can petition to upload docs to any organization (including ones that do not exist yet) with `public` visibility. The petition gets sent to all editors (or a designated editor if stipulated in that organization's settings), where the editor can decide to approve as-is, modify and then approve, or decline.

The upload gets approved automatically after 7 days if a) no editor approves or declines the petition and b) the petition is directed at the user’s billing organization.
If the petition is not directed at the user’s billing organization, the petition gets renewed for another 7 days and gets redirected to the user’s billing organization (with the nominal organization remaining as the original target).

If the organization does not exist, the superadmin (site admin) reviews the request, and can decide whether to create the organization, add the document to an existing organization, or send the petition to the user’s billing organization. If the user sending the petition is an editor or an admin (or is a member with embedding credits left over), they can choose to offer to pay for the embedding.
