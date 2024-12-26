import React, { useRef, useEffect, useState } from 'react';
import { pdfjs } from 'react-pdf';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface PDFViewerProps {
  fileUrl: string;
  initialPage: number;
}

const PDFViewer = ({ fileUrl, initialPage }: PDFViewerProps) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(initialPage);
  const [pdfDoc, setPdfDoc] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [renderLock, setRenderLock] = useState<boolean>(false);

  const renderPage = async (pageNum: number, pdf: any) => {
    if (renderLock) {
      console.warn('Render is locked, skipping page render');
      return;
    }

    setRenderLock(true);

    try {
      const page = await pdf.getPage(pageNum);
      const containerWidth = containerRef.current?.offsetWidth || window.innerWidth;
      const targetHeight = (containerWidth * 5) / 3; // 3:5 aspect ratio

      const naturalViewport = page.getViewport({ scale: 1.0 });
      const scaleX = containerWidth / naturalViewport.width;
      const scaleY = targetHeight / naturalViewport.height;
      const scaleToUse = Math.min(scaleX, scaleY) * 0.95;

      const scaledViewport = page.getViewport({ scale: scaleToUse });

      const canvas = canvasRef.current;
      const context = canvas?.getContext('2d');

      if (canvas && context) {
        context.clearRect(0, 0, canvas.width, canvas.height);
        canvas.width = scaledViewport.width;
        canvas.height = scaledViewport.height;

        const renderContext = {
          canvasContext: context,
          viewport: scaledViewport,
        };

        await page.render(renderContext).promise;
      }

      setRenderLock(false);
    } catch (error) {
      console.error(`Error rendering page ${pageNum}:`, error);
      setRenderLock(false);
    }
  };

  useEffect(() => {
    const loadPDF = async () => {
      try {
        setIsLoading(true);
        const pdf = await pdfjs.getDocument(fileUrl).promise;
        setNumPages(pdf.numPages);
        setPdfDoc(pdf);
        renderPage(currentPage, pdf);
      } catch (error) {
        console.error('Error loading PDF:', error);
      }
    };

    loadPDF();
  }, [fileUrl]);

  useEffect(() => {
    if (pdfDoc) {
      renderPage(currentPage, pdfDoc);
    }
  }, [currentPage, pdfDoc]);

  useEffect(() => {
    if (pdfDoc) {
      const simulateNavigation = async () => {
        await new Promise((resolve) => setTimeout(resolve, 500));
        setCurrentPage((prevPage) => Math.min(prevPage + 1, numPages || 1));
        await new Promise((resolve) => setTimeout(resolve, 500));
        setCurrentPage(initialPage);
        setIsLoading(false);
      };
      simulateNavigation();
    }
  }, [pdfDoc, initialPage]);

  const goToPrevPage = () => {
    setCurrentPage((prevPage) => Math.max(prevPage - 1, 1));
  };

  const goToNextPage = () => {
    setCurrentPage((prevPage) => (numPages ? Math.min(prevPage + 1, numPages) : prevPage));
  };

  const containerStyle = {
    ...styles.container,
    aspectRatio: '3/5',
    maxHeight: '80vh',
  };

  const canvasContainerStyle = {
    position: 'relative' as const,
    width: '100%',
    height: '100%',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'hidden',
  };

  return (
    <div ref={containerRef} style={containerStyle}>
      {isLoading ? (
        <div style={styles.loadingContainer}>
          <div className="loading-gif">Loading...</div>
        </div>
      ) : (
        <>
          <div style={styles.navigation}>
            <button
              onClick={goToPrevPage}
              disabled={currentPage <= 1}
              style={currentPage <= 1 ? styles.arrowDisabled : styles.arrow}
            >
              ◄
            </button>
          </div>
          <div style={canvasContainerStyle}>
            <canvas ref={canvasRef} style={styles.canvas} />
          </div>
          <div style={styles.navigation}>
            <button
              onClick={goToNextPage}
              disabled={currentPage >= (numPages || 0)}
              style={currentPage >= (numPages || 0) ? styles.arrowDisabled : styles.arrow}
            >
              ►
            </button>
          </div>
          <div style={styles.controls}>
            <span style={styles.pageInfo}>
              Page {currentPage} of {numPages}
            </span>
          </div>
        </>
      )}
    </div>
  );
};

const styles = {
  container: {
    width: '100%',
    display: 'flex',
    flexDirection: 'row' as const,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative' as const,
    backgroundColor: 'transparent',
  },
  canvas: {
    maxWidth: '100%',
    maxHeight: '100%',
    objectFit: 'contain' as const,
  },
  loadingContainer: {
    width: '100%',
    height: '100%',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  },
  navigation: {
    width: '50px',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  },
  controls: {
    position: 'absolute' as const,
    bottom: '20px',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    width: '100%',
  },
  arrow: {
    backgroundColor: 'transparent',
    border: 'none',
    color: '#A9A9A9',
    fontSize: '2rem',
    cursor: 'pointer',
    padding: '10px',
    borderRadius: '50%',
  },
  arrowDisabled: {
    backgroundColor: 'transparent',
    border: 'none',
    color: '#A9A9A9',
    fontSize: '2rem',
    cursor: 'not-allowed',
    padding: '10px',
    borderRadius: '50%',
  },
  pageInfo: {
    fontSize: '16px',
    color: '#333',
    marginBottom: '10px'
  },
};

export default PDFViewer;
