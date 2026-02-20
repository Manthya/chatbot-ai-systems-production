import { useState } from 'react';

export interface UploadResult {
    id: string;
    filename: string;
    type: string;
    file_path: string;
}

export const useUpload = () => {
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const uploadFile = async (file: File): Promise<UploadResult | null> => {
        setIsUploading(true);
        setError(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('http://localhost:8000/api/upload', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Upload failed');
            }

            const data = await response.json();
            return data;
        } catch (err: any) {
            setError(err.message);
            console.error('Upload Error:', err);
            return null;
        } finally {
            setIsUploading(false);
        }
    };

    return { uploadFile, isUploading, uploadError: error };
};
