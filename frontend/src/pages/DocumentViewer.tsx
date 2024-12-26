// DocumentViewer.tsx
import React, { useMemo, useContext } from "react";
import { useParams, useLocation, Link, useNavigate } from "react-router-dom";
import { UserContext } from "../context/UserContext";
import { ThemeContext } from "../context/ThemeContext";
import PDFViewerChat from "../components/PDFViewerChat";

const DocumentViewer: React.FC = () => {
  const { filename } = useParams<{ filename: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useContext(UserContext);
  const { theme } = useContext(ThemeContext);

  const [error, setError] = React.useState<string | null>(null);

  // Extract the page number from the URL.
  const pathParts = location.pathname.split("/");
  const pageNumber = parseInt(
    pathParts[pathParts.length - 1].split("?")[0],
    10
  );

  const chatId = useMemo(
    () => new URLSearchParams(location.search).get("chat_id"),
    [location.search]
  );

  const backendUrl = useMemo(() => {
    const backendUrl =
      import.meta.env.VITE_REACT_APP_BACKEND_URL || "http://127.0.0.1:5000";
    const url = `${backendUrl}/api/tmp/${filename}?chat_id=${chatId}&cache_bust=${new Date().getTime()}`;
    return url;
  }, [filename, chatId]);

  const handleLogout = async () => {
    // Logic for logging out
    logout();
    navigate("/");
  };

  const styles = {
    container: {
      textAlign: "center",
      backgroundColor: theme === "light" ? "#F5F5F5" : "#1a1a1a",
      color: theme === "light" ? "#333333" : "#FFFFFF",
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      justifyContent: "center",
      alignItems: "center",
      padding: "40px 20px",
    },
    headerContainer: {
      display: "flex",
      justifyContent: "space-between",
      width: "100%",
      maxWidth: "800px",
      padding: "10px 20px",
      backgroundColor: theme === "light" ? "#FFFFFF" : "#333333",
      boxShadow: "0 2px 4px rgba(0, 0, 0, 0.1)",
      borderRadius: "8px",
      marginBottom: "30px",
    },
    header: {
      fontSize: "24px",
      fontWeight: 600,
      color: theme === "light" ? "#1A1A1A" : "#FFFFFF",
    },
    link: {
      color: theme === "light" ? "#0066CC" : "#A9A9A9",
      textDecoration: "none",
      fontWeight: 500,
    },
    button: {
      backgroundColor: "transparent",
      border: "none",
      color: theme === "light" ? "#800000" : "#A9A9A9",
      cursor: "pointer",
      fontSize: "16px",
      fontWeight: 500,
    },
    content: {
      width: "100%",
      maxWidth: "800px",
      padding: "20px",
      backgroundColor: theme === "light" ? "#FFFFFF" : "#333333",
      borderRadius: "8px",
      boxShadow: "0 2px 4px rgba(0, 0, 0, 0.1)",
    },
    error: {
      color: "#FF0000",
    },
  } as const;

  return (
    <div style={styles.container}>
      <div style={styles.content}>
        {error && <div style={styles.error}>{error}</div>}
        {!error && (
          // Pass the URL and page number as props to PDFViewerChat
          <PDFViewerChat fileUrl={backendUrl} initialPage={pageNumber} />
        )}
      </div>
    </div>
  );
};

export default DocumentViewer;
