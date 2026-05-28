import { useEffect, useState, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import Header from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  Upload,
  FileText,
  Send,
  Bot,
  User,
  Loader2,
  Trash2,
  ChevronRight,
  Clock,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAuth } from "@/hooks/useAuth";
import { Viewer, Worker } from "@react-pdf-viewer/core";
import { defaultLayoutPlugin } from "@react-pdf-viewer/default-layout";
import { pageNavigationPlugin } from "@react-pdf-viewer/page-navigation";
import "@react-pdf-viewer/core/lib/styles/index.css";
import "@react-pdf-viewer/default-layout/lib/styles/index.css";

interface FileRecord {
  id: string;
  name: string;
  kbId: string;
  createdAt: string;
  status: string;
}

interface Chunk {
  text: string;
  source: string;
  score: number;
  page_number?: number;
}

interface ChatMessage {
  id: string;
  role: "user" | "ai";
  content: string;
  source?: string;
  chunks?: Chunk[];
}

export default function KBDetailPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const kbId = searchParams.get("kb_id");
  const [kbName, setKbName] = useState<string>("Knowledge Base");
  const { user } = useAuth();

  const [files, setFiles] = useState<FileRecord[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [deletingFileId, setDeletingFileId] = useState<string | null>(null);

  // PDF Viewer states
  const [activeDocumentUrl, setActiveDocumentUrl] = useState<string | null>(
    null,
  );
  const [activeDocumentName, setActiveDocumentName] = useState<string | null>(
    null,
  );
  const [activeDocumentId, setActiveDocumentId] = useState<string | null>(null);
  const [activeMdContent, setActiveMdContent] = useState<string | null>(null);
  const [isPdfLoading, setIsPdfLoading] = useState(false);
  const [pendingPageJump, setPendingPageJump] = useState<number | null>(null);
  const pageNavPluginInstance = pageNavigationPlugin();
  const { jumpToPage } = pageNavPluginInstance;
  const defaultLayoutPluginInstance = defaultLayoutPlugin();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!kbId) {
      navigate("/knowledge-bases");
      return;
    }
    if (!user) {
      navigate("/");
      return;
    }
    setKbName(kbId);

    // Load chat history from localStorage
    const saved = localStorage.getItem(`dochub_chat_${user.username}_${kbId}`);
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch {
        /* ignore */
      }
    } else {
      setMessages([]);
    }
    setHistoryLoaded(true);

    const fetchDocuments = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL;
        if (!apiUrl) return;
        const res = await fetch(`${apiUrl}/documents?workspace_id=${kbId}`, {
          headers: { Authorization: `Bearer ${user.idToken}` },
        });
        if (res.ok) {
          const data = await res.json();
          const fetchedFiles = data.documents.map((d: any) => ({
            id: d.document_id,
            name: d.filename,
            kbId: kbId as string,
            createdAt: new Date(d.created_at || Date.now()).toLocaleDateString(
              "en-GB",
            ),
            status: d.status,
          }));
          setFiles(fetchedFiles);
        }
      } catch (err) {
        console.error("Failed to load documents", err);
      }
    };
    fetchDocuments();
    const interval = setInterval(fetchDocuments, 10000);
    return () => clearInterval(interval);
  }, [kbId, user, navigate]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  // Save chat history to localStorage
  useEffect(() => {
    if (historyLoaded && user && kbId) {
      if (messages.length > 0) {
        localStorage.setItem(
          `dochub_chat_${user.username}_${kbId}`,
          JSON.stringify(messages),
        );
      } else {
        localStorage.removeItem(`dochub_chat_${user.username}_${kbId}`);
      }
    }
  }, [messages, historyLoaded, user, kbId]);

  const handleClearHistory = () => {
    if (user && kbId) {
      localStorage.removeItem(`dochub_chat_${user.username}_${kbId}`);
      setMessages([]);
      toast.success("Đã xóa lịch sử chat");
    }
  };

  const handleFileUploadTrigger = () => {
    fileInputRef.current?.click();
  };

  const handleDeleteFile = async (fileId: string) => {
    if (!user) return;
    setDeletingFileId(fileId);
    try {
      const apiUrl = import.meta.env.VITE_API_URL;
      if (apiUrl) {
        const res = await fetch(`${apiUrl}/documents/${fileId}`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${user.idToken}` },
        });
        if (!res.ok) throw new Error("Delete failed");
      }
      setFiles((prev) => prev.filter((f) => f.id !== fileId));
      toast.success("Đã xóa tài liệu");
    } catch (err) {
      console.error("Delete file error:", err);
      toast.error("Xóa tài liệu thất bại.");
    } finally {
      setDeletingFileId(null);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !user) return;

    setIsUploading(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL;
      if (!apiUrl) {
        toast.error("Chưa cấu hình VITE_API_URL");
        setIsUploading(false);
        return;
      }
      const initRes = await fetch(`${apiUrl}/documents/upload`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user.idToken}`,
        },
        body: JSON.stringify({ workspace_id: kbId, filename: file.name }),
      });
      const initData = await initRes.json();
      if (!initRes.ok)
        throw new Error(initData.error || "Failed to init upload");

      const { upload_url } = initData;
      const formData = new FormData();
      Object.keys(upload_url.fields).forEach((key) =>
        formData.append(key, upload_url.fields[key]),
      );
      formData.append("file", file);
      const s3Res = await fetch(upload_url.url, {
        method: "POST",
        body: formData,
      });
      if (!s3Res.ok) throw new Error("Failed to upload to S3");

      setFiles((prev) => [
        ...prev,
        {
          id: initData.document_id,
          name: file.name,
          kbId: kbId as string,
          createdAt: new Date().toLocaleDateString("en-GB"),
          status: "PENDING",
        },
      ]);
      if (fileInputRef.current) fileInputRef.current.value = "";
      toast.success(`Đã tải lên: ${file.name}`);
    } catch (error) {
      console.error("Upload error:", error);
      toast.error("Tải lên thất bại. Vui lòng kiểm tra console.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || !user) return;

    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: "user",
      content: inputValue.trim(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setIsThinking(true);

    try {
      const aiUrl = import.meta.env.VITE_API_URL;
      if (!aiUrl) throw new Error("Chưa cấu hình VITE_API_URL");

      const response = await fetch(`${aiUrl}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user.idToken}`,
        },
        body: JSON.stringify({ 
          query: userMsg.content, 
          workspace_id: kbId,
          history: messages 
        }),
      });

      if (!response.ok) throw new Error("Lỗi khi gọi AI Backend");

      const data = await response.json();
      const aiMsg: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        role: "ai",
        content: data.answer,
        source: data.sources?.length > 0 ? data.sources.join(", ") : undefined,
        chunks: data.chunks || [],
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (error) {
      console.error("Chat error:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: `msg_${Date.now() + 1}`,
          role: "ai",
          content:
            "Xin lỗi, đã có lỗi xảy ra khi kết nối tới AI. Vui lòng thử lại sau.",
        },
      ]);
    } finally {
      setIsThinking(false);
    }
  };

  const processContent = (content: string) => {
    return content.replace(/\[[^\]]*Source\s*\d+[^\]]*\]/gi, (match) => {
      const numbers = match.match(/\d+/g);
      if (!numbers) return match;
      const cleanMatch = match.replace(/[\[\]]/g, "");
      const cleanIndices = numbers.join(",");
      return `[${cleanMatch}](#source-${cleanIndices})`;
    });
  };

  const handleFileClick = async (file: FileRecord) => {
    if (!user) return;
    const isPdf = file.name.toLowerCase().endsWith(".pdf");
    const isMd = file.name.toLowerCase().endsWith(".md");

    if (!isPdf && !isMd) {
      toast.error("Hiện tại hệ thống chỉ hỗ trợ xem trực tiếp file PDF và MD.");
      return;
    }

    setIsPdfLoading(true);
    setActiveDocumentName(file.name);
    setActiveDocumentId(file.id);
    setActiveMdContent(null);
    setActiveDocumentUrl(null);
    try {
      const apiUrl = import.meta.env.VITE_API_URL;
      const res = await fetch(`${apiUrl}/documents/${file.id}`, {
        headers: { Authorization: `Bearer ${user.idToken}` },
      });
      if (!res.ok) throw new Error("Lỗi lấy thông tin file");
      const data = await res.json();
      const doc = data.document || data;
      const url = doc.view_url || doc.download_url || doc.url;

      if (isPdf) {
        setActiveDocumentUrl(url);
        setActiveMdContent(null);
      } else if (isMd) {
        const mdRes = await fetch(url);
        const mdText = await mdRes.text();
        setActiveMdContent(mdText);
        setActiveDocumentUrl(null);
      }
    } catch (err) {
      console.error("Error loading file:", err);
      toast.error("Không thể tải file.");
      setActiveDocumentName(null);
      setActiveDocumentId(null);
    } finally {
      setIsPdfLoading(false);
    }
  };

  const handleChunkClick = async (chunk: Chunk) => {
    const file = files.find((f) => f.name === chunk.source);
    if (!file) {
      toast.error(`Không tìm thấy file nguồn: ${chunk.source}`);
      return;
    }

    const isPdf = file.name.toLowerCase().endsWith(".pdf");
    const isMd = file.name.toLowerCase().endsWith(".md");

    if (activeDocumentName !== file.name) {
      if (isPdf && chunk.page_number) {
        setPendingPageJump(chunk.page_number);
      }
      await handleFileClick(file);
    } else if (isPdf && chunk.page_number) {
      jumpToPage(chunk.page_number - 1);
    }

    if (isMd) {
      const words = chunk.text
        .trim()
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 6)
        .join(" ");
      setTimeout(() => {
        (window as any).find(words, false, false, true, false, true, false);
      }, 500);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-white">
      <Header />

      <main className="flex-1 overflow-hidden flex flex-col md:flex-row">
        {/* Left Column - Document Sources */}
        <div className="w-full md:w-1/4 xl:w-1/5 border-r border-slate-200 flex flex-col bg-slate-50/50">
          <div className="p-4 border-b border-slate-200">
            <Button
              variant="ghost"
              size="sm"
              className="mb-4 text-slate-500 hover:text-slate-900 -ml-2"
              onClick={() => navigate("/knowledge-bases")}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Knowledge Bases
            </Button>
            <h2 className="font-semibold text-lg truncate" title={kbName}>
              {kbName}
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Manage documents & sources
            </p>
          </div>

          <div className="p-4">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              className="hidden"
              accept=".pdf,.docx,.md"
            />
            <Button
              className="w-full bg-slate-900 text-white hover:bg-slate-800"
              onClick={handleFileUploadTrigger}
              disabled={isUploading}
            >
              {isUploading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Upload className="h-4 w-4 mr-2" />
              )}
              {isUploading ? "Đang tải lên..." : "+ Upload File"}
            </Button>
            <p className="text-[10px] text-center text-slate-500 mt-2">
              Accepts .pdf, .docx, .md
            </p>
          </div>

          <div className="flex-1 overflow-y-auto px-4 pb-4">
            <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-3">
              Uploaded Files ({files.length})
            </h3>

            {files.length === 0 ? (
              <div className="text-center py-8 text-sm text-slate-500">
                No files uploaded yet.
              </div>
            ) : (
              <ul className="space-y-2">
                {files.map((file) => (
                  <li
                    key={file.id}
                    className={`group/file relative flex items-start gap-2 p-3 rounded-md border shadow-sm transition-colors cursor-pointer ${
                      activeDocumentId === file.id
                        ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500/30"
                        : "bg-white border-slate-200 hover:border-blue-300"
                    }`}
                    onClick={() => handleFileClick(file)}
                  >
                    <FileText className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <span
                        className="text-sm text-slate-700 truncate block"
                        title={file.name}
                      >
                        {file.name}
                      </span>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] text-slate-400">
                          {file.createdAt}
                        </span>
                        {file.status === "READY" ? (
                          <Badge
                            variant="secondary"
                            className="text-[10px] px-1.5 py-0 bg-green-50 text-green-700 border-green-200"
                          >
                            <CheckCircle2 className="h-2.5 w-2.5 mr-0.5" />{" "}
                            Ready
                          </Badge>
                        ) : file.status === "INDEXING" ? (
                          <Badge
                            variant="secondary"
                            className="text-[10px] px-1.5 py-0 bg-blue-50 text-blue-700 border-blue-200"
                          >
                            <Loader2 className="h-2.5 w-2.5 mr-0.5 animate-spin" />{" "}
                            Indexing
                          </Badge>
                        ) : file.status === "ERROR" ? (
                          <Badge
                            variant="secondary"
                            className="text-[10px] px-1.5 py-0 bg-red-50 text-red-700 border-red-200"
                          >
                            <AlertCircle className="h-2.5 w-2.5 mr-0.5" />{" "}
                            Error
                          </Badge>
                        ) : (
                          <Badge
                            variant="secondary"
                            className="text-[10px] px-1.5 py-0 bg-amber-50 text-amber-700 border-amber-200"
                          >
                            <Clock className="h-2.5 w-2.5 mr-0.5" /> Pending
                          </Badge>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteFile(file.id);
                      }}
                      disabled={deletingFileId === file.id}
                      className="absolute right-2 top-2 opacity-0 group-hover/file:opacity-100 transition-opacity p-1.5 rounded text-slate-400 hover:text-red-500 hover:bg-red-50 shrink-0"
                      title="Delete document"
                    >
                      {deletingFileId === file.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Middle Column - PDF Viewer */}
        <div className="hidden md:flex flex-1 border-r border-slate-200 flex-col bg-slate-100 relative">
          {isPdfLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                <span className="text-sm text-slate-500">
                  Đang tải tài liệu...
                </span>
              </div>
            </div>
          ) : null}

          {activeDocumentUrl ? (
            <div className="h-full w-full">
              <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
                <Viewer
                  fileUrl={activeDocumentUrl}
                  plugins={[defaultLayoutPluginInstance, pageNavPluginInstance]}
                  onDocumentLoad={() => {
                    if (pendingPageJump) {
                      setTimeout(() => {
                        jumpToPage(pendingPageJump! - 1);
                        setPendingPageJump(null);
                      }, 300);
                    }
                  }}
                />
              </Worker>
            </div>
          ) : activeMdContent ? (
            <div className="h-full w-full overflow-y-auto bg-white p-8">
              <article className="prose prose-sm md:prose-base prose-slate max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {activeMdContent}
                </ReactMarkdown>
              </article>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400">
              <div className="text-center">
                <FileText className="h-16 w-16 mx-auto mb-4 opacity-30" />
                <p className="text-sm">Chọn một tài liệu để xem</p>
              </div>
            </div>
          )}
        </div>

        {/* Right Column - AI Chat */}
        <div className="w-full md:w-[35%] xl:w-[30%] flex flex-col h-full bg-white relative">
          <div className="flex items-center justify-between px-4 py-2 border-b border-slate-200">
            <span className="text-sm font-medium text-slate-700">AI Chat</span>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-slate-400 hover:text-red-500"
              onClick={handleClearHistory}
            >
              Xóa lịch sử
            </Button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "ai" && (
                  <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0 border border-blue-200">
                    <Bot className="h-5 w-5 text-blue-600" />
                  </div>
                )}

                <div
                  className={`flex flex-col gap-1 max-w-[85%] ${msg.role === "user" ? "items-end" : "items-start"}`}
                >
                  <div
                    className={`px-4 py-3 rounded-2xl text-sm ${
                      msg.role === "user"
                        ? "bg-blue-600 text-white rounded-tr-sm"
                        : "bg-slate-100 text-slate-900 rounded-tl-sm"
                    }`}
                  >
                    {msg.role === "ai" ? (
                      <div className="prose prose-sm max-w-none prose-slate">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            a: ({ node, href, children, ...props }) => {
                              if (href?.startsWith("#source-")) {
                                return (
                                  <a
                                    href={href}
                                    title={String(children)}
                                    className="inline-flex items-center align-middle px-1.5 py-0.5 mx-0.5 rounded bg-blue-50 text-blue-600 hover:bg-blue-100 text-[11px] font-medium no-underline border border-blue-200 transition-colors cursor-pointer max-w-[150px] overflow-hidden whitespace-nowrap"
                                    onClick={(e) => {
                                      e.preventDefault();
                                      const indicesStr = href.replace(
                                        "#source-",
                                        "",
                                      );
                                      if (
                                        indicesStr &&
                                        msg.chunks &&
                                        msg.chunks.length > 0
                                      ) {
                                        const index =
                                          parseInt(
                                            indicesStr.split(",")[0],
                                            10,
                                          ) - 1;
                                        const chunk = msg.chunks[index];
                                        if (chunk) handleChunkClick(chunk);
                                      }
                                    }}
                                    {...props}
                                  >
                                    <FileText className="h-3 w-3 mr-1 shrink-0" />
                                    <span className="truncate">{children}</span>
                                  </a>
                                );
                              }
                              return (
                                <a href={href} {...props}>
                                  {children}
                                </a>
                              );
                            },
                          }}
                        >
                          {processContent(msg.content)}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      msg.content
                    )}
                  </div>

                  {msg.chunks && msg.chunks.length > 0 && (
                    <details className="mt-2 w-full group">
                      <summary className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5 cursor-pointer hover:text-slate-700 list-none flex items-center select-none">
                        <ChevronRight className="h-3 w-3 mr-1 transition-transform group-open:rotate-90" />
                        Sources ({msg.chunks.length})
                      </summary>
                      <div className="space-y-1.5 max-h-[200px] overflow-y-auto pr-1">
                        {msg.chunks.map((chunk, i) => (
                          <div
                            key={i}
                            onClick={() => handleChunkClick(chunk)}
                            className="bg-white p-2.5 rounded-lg border border-slate-200 hover:border-blue-300 hover:shadow-sm transition-all cursor-pointer group/chunk"
                          >
                            <div className="flex items-center gap-1.5 mb-1">
                              <FileText className="h-3 w-3 text-blue-500" />
                              <span className="text-[11px] font-medium text-blue-600 truncate">
                                {chunk.source}
                              </span>
                              {chunk.page_number && (
                                <span className="text-[10px] text-slate-400 ml-auto">
                                  p.{chunk.page_number}
                                </span>
                              )}
                              <ChevronRight className="h-3 w-3 text-slate-300 group-hover/chunk:text-blue-400 transition-colors ml-auto shrink-0" />
                            </div>
                            <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
                              {chunk.text.substring(0, 150)}...
                            </p>
                            <div className="mt-1">
                              <span className="text-[9px] text-slate-400">
                                Score: {(chunk.score * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </div>

                {msg.role === "user" && (
                  <div className="h-8 w-8 rounded-full bg-slate-200 flex items-center justify-center shrink-0 border border-slate-300">
                    <User className="h-5 w-5 text-slate-600" />
                  </div>
                )}
              </div>
            ))}

            {isThinking && (
              <div className="flex gap-3 justify-start">
                <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0 border border-blue-200">
                  <Bot className="h-5 w-5 text-blue-600" />
                </div>
                <div className="px-4 py-3 rounded-2xl text-sm bg-slate-100 text-slate-900 rounded-tl-sm flex items-center gap-2">
                  <span className="h-2 w-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                  <span className="h-2 w-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                  <span className="h-2 w-2 bg-slate-400 rounded-full animate-bounce"></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="p-4 bg-white border-t border-slate-200">
            <form
              onSubmit={handleSendMessage}
              className="max-w-3xl mx-auto relative flex items-center"
            >
              <Input
                value={inputValue}
                onChange={(e: any) => setInputValue(e.target.value)}
                placeholder="Ask a question about your documents..."
                className="pr-12 py-6 rounded-full border-slate-300 shadow-sm focus-visible:ring-blue-500"
                disabled={isThinking}
              />
              <Button
                type="submit"
                size="icon"
                className="absolute right-1.5 h-9 w-9 rounded-full bg-blue-600 hover:bg-blue-700"
                disabled={!inputValue.trim() || isThinking}
              >
                <Send className="h-4 w-4 text-white" />
              </Button>
            </form>
            <div className="text-center mt-2">
              <p className="text-[10px] text-slate-400">
                AI can make mistakes. Check important information.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
