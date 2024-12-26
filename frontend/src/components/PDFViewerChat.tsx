import React, { useRef, useEffect, useState } from 'react';
import { pdfjs } from 'react-pdf';
import '../styles/PDFViewerChat.css';
import rightArrow from '../assets/images/right-arrow.png';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface PDFViewerChatProps {
  fileUrl: string;
  initialPage: number;
}

const PDFViewerChat = ({ fileUrl, initialPage }: PDFViewerChatProps) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(initialPage);
  const [inputPage, setInputPage] = useState<string>('');
  const [pdfDoc, setPdfDoc] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [renderLock, setRenderLock] = useState<boolean>(false);

  // Get the backend URL from environment variables
  const backendUrl = import.meta.env.VITE_REACT_APP_BACKEND_URL;

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
        // Use the environment variable for the backend URL
        const pdfUrl = fileUrl.startsWith('http') ? fileUrl : `${backendUrl}${fileUrl}`;
        const pdf = await pdfjs.getDocument(pdfUrl).promise;
        setNumPages(pdf.numPages);
        setPdfDoc(pdf);
        renderPage(currentPage, pdf);
      } catch (error) {
        console.error('Error loading PDF:', error);
        setError('Failed to load PDF. Please try again.');
      }
    };

    loadPDF();
  }, [fileUrl, backendUrl]);

  useEffect(() => {
    if (pdfDoc) {
      renderPage(currentPage, pdfDoc);
    }
  }, [currentPage, pdfDoc]);

  useEffect(() => {
    if (pdfDoc) {
      const simulateNavigation = async () => {
        await new Promise((resolve) => setTimeout(resolve, 500));
        setCurrentPage((prevPage) => Math.min(prevPage - 1, numPages || 1));
        await new Promise((resolve) => setTimeout(resolve, 500));
        setCurrentPage(initialPage);
        setIsLoading(false);
      };
      simulateNavigation();
    }
  }, [pdfDoc, initialPage, numPages]);

  const goToPrevPage = () => {
    setCurrentPage((prevPage) => Math.max(prevPage - 1, 1));
  };

  const goToNextPage = () => {
    setCurrentPage((prevPage) => (numPages ? Math.min(prevPage + 1, numPages) : prevPage));
  };

  const handlePageInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputPage(e.target.value);
  };

  const jumpToPage = () => {
    const pageNumber = parseInt(inputPage, 10);
    if (!isNaN(pageNumber) && pageNumber > 0 && pageNumber <= (numPages || 0)) {
      setCurrentPage(pageNumber);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      jumpToPage();
    }
  };

  if (error) {
    return <div className="pdf-error">{error}</div>;
  }

  return (
    <div ref={containerRef} className="pdf-viewer-container">
      {isLoading ? (
        <div className="page-info">Loading PDF...</div>
      ) : (
        <>
          <div className="button-container">
            <button
              onClick={goToPrevPage}
              disabled={currentPage <= 1}
              className={`nav-button prev-button ${currentPage <= 1 ? 'button-disabled' : ''}`}
            >
              <img src={rightArrow} alt="Previous Page" className="nav-icon" />
            </button>
            <button
              onClick={goToNextPage}
              disabled={currentPage >= (numPages || 0)}
              className={`nav-button next-button ${currentPage >= (numPages || 0) ? 'button-disabled' : ''}`}
            >
              <img src={rightArrow} alt="Next Page" className="nav-icon" />
            </button>
          </div>
          <div className="canvas-container">
            <canvas ref={canvasRef} className="pdf-viewer-canvas"></canvas>
          </div>
          <div className="page-info">
            Page {currentPage} of {numPages}
          </div>
          <div className="pdf-input-container">
            <input
              type="text"
              value={inputPage}
              onChange={handlePageInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Page"
              className="pdf-input"
            />
            <button onClick={jumpToPage} className="input-button">
              Go
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default PDFViewerChat;
