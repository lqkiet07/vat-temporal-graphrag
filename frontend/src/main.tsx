import React, { Component, ErrorInfo, ReactNode } from "react";
import { createRoot } from "react-dom/client";
import App from "./app/App.tsx";
import "./styles/index.css";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error in React render:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "24px",
          background: "#F8FAFC",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          color: "#0F172A",
        }}>
          <div style={{
            maxWidth: "480px",
            background: "#FFFFFF",
            padding: "28px",
            borderRadius: "20px",
            border: "1px solid #CBD5E1",
            boxShadow: "0 10px 25px -5px rgba(0,0,0,0.08)",
            textAlign: "center",
          }}>
            <div style={{ fontSize: "36px", marginBottom: "12px" }}>⚠️</div>
            <h2 style={{ fontSize: "17px", fontWeight: "700", color: "#1E3A8A", margin: "0 0 8px 0" }}>
              Đã phát sinh sự cố giao diện
            </h2>
            <p style={{ fontSize: "13px", color: "#64748B", margin: "0 0 16px 0", lineHeight: "1.5" }}>
              {this.state.error?.message || "Đã xảy ra lỗi không xác định trong quá trình kết xuất."}
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                background: "#1E3A8A",
                color: "#FFFFFF",
                border: "none",
                borderRadius: "9999px",
                padding: "8px 20px",
                fontSize: "13px",
                fontWeight: "600",
                cursor: "pointer",
              }}
            >
              Tải lại ứng dụng
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

createRoot(document.getElementById("root")!).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>
);
