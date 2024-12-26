import React, { useState, useEffect } from 'react';
import PDFViewer from './PDFViewerLibrary'; // Your existing PDFViewer component

interface MiniPDFViewerProps {
  documentLink: string;
  initialPage: number;
}

const MiniPDFViewer: React.FC<MiniPDFViewerProps> = ({ documentLink, initialPage }) => {
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [pdfData, setPdfData] = useState<ArrayBuffer | null>(null);
  const [renderKey, setRenderKey] = useState<number>(0); // Key to force remounting

  useEffect(() => {
    // Fetch PDF data when the document link changes
    const fetchPDF = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(documentLink);
        if (!response.ok) {
          throw new Error('Failed to load the PDF');
        }
        const blob = await response.blob();
        const arrayBuffer = await blob.arrayBuffer();
        setPdfData(arrayBuffer);
        setIsLoading(false);

        // Force a re-render by updating the key after loading the PDF
        setRenderKey((prevKey) => prevKey + 1);
      } catch (error) {
        console.error('Error fetching PDF:', error);
        setError('Failed to load the document');
        setIsLoading(false);
      }
    };

    fetchPDF();
  }, [documentLink]);

  return (
    <div style={styles.container}>
      {isLoading && <div>Loading PDF...</div>}
      {error && <div style={styles.error}>{error}</div>}
      {pdfData && (
        <PDFViewer
          key={renderKey} // Assign a dynamic key to force remount on load
          fileUrl={URL.createObjectURL(new Blob([pdfData]))} // Create URL from the PDF data
          initialPage={initialPage} // Pass the initial page prop
        />
      )}
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as 'column',
    justifyContent: 'center',
    alignItems: 'center',
    width: '100%',
    height: '100%', // Make sure it takes the full height available
  },
  error: {
    color: 'red',
  },
};

export default MiniPDFViewer;
