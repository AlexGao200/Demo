import { useState } from 'react';
import axiosInstance from '../axiosInstance';

interface UseQRCodeOptions {
  onSuccess?: (link: string) => void;
  onError?: (error: string) => void;
}

interface QRCodeData {
  chat_id: string;
  chat_link: string;
  titles: string[];
  original_document_ids: string[];
  expires_at: string;
}

interface ApiError {
  response?: {
    data?: {
      error?: string;
    };
  };
}

export const useQRCode = (options: UseQRCodeOptions = {}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [shareLink, setShareLink] = useState<string>('');

  const generateQRCode = async (documentIds: string[]) => {
    try {
      console.log('Generating QR code for documents:', documentIds);
      setIsLoading(true);
      setError('');

      const { data } = await axiosInstance.post<QRCodeData>('/create_qr_code', {
        document_ids: documentIds
      });

      console.log('Generated QR code data:', data);
      setShareLink(data.chat_link);
      options.onSuccess?.(data.chat_link);
      return data;
    } catch (err) {
      console.error('QR code generation failed:', err);
      const apiError = err as ApiError;
      const errorMessage = apiError?.response?.data?.error || 'Failed to create QR code';
      setError(errorMessage);
      options.onError?.(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const sendQRCodeEmail = async (email: string, link: string, documentTitle: string) => {
    try {
      console.log('Sending QR code email:', { email, link, documentTitle });
      setIsLoading(true);
      setError('');

      await axiosInstance.post('/send_qr_code_email', {
        email,
        link,
        document_title: documentTitle,
      });

      console.log('Email sent successfully');
      return true;
    } catch (err) {
      console.error('Email sending failed:', err);
      const apiError = err as ApiError;
      const errorMessage = apiError?.response?.data?.error || 'Failed to send email';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const regenerateAndGetLink = async (documentIds: string[]) => {
    console.log('Regenerating QR code for documents:', documentIds);
    const data = await generateQRCode(documentIds);
    console.log('Regenerated QR code with new link:', data.chat_link);
    return data.chat_link;
  };

  return {
    generateQRCode,
    sendQRCodeEmail,
    regenerateAndGetLink,
    isLoading,
    error,
    shareLink
  };
};
