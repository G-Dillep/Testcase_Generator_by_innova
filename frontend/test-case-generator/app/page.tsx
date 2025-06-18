"use client"

import { useState, useEffect, useRef } from "react"
import {
  MessageCircle,
  X,
  Download,
  Search,
  Eye,
  Triangle,
  AlertCircle,
  Linkedin,
  Facebook,
  Twitter,
  Instagram,
  Youtube,
  Music,
  ChevronLeft,
  ChevronRight,
  Clock,
  ArrowRight,
  FileText,
  RefreshCw,
  Calendar,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useRouter } from "next/navigation"
import { api, Story } from "@/lib/api"
import { toast } from "sonner"
import { Select } from "@/components/ui/select"

interface FormData {
  storyId: string
  storyDescription: string
  createdDate: string
  fromDate: string
  toDate: string
  priority?: string
  category?: string
  assignee?: string
}

interface TestCase {
  storyId: string
  storyDescription: string
  testCaseCount: number
  processStartTime: string
  processEndTime: string
  testCaseCreatedTime: string
  status?: "completed" | "in-progress" | "pending" | "failed"
  priority?: "high" | "medium" | "low"
  category?: string
  coverage?: number
  assignee?: string
}

interface DashboardStats {
  totalTestCases: number
  completedTestCases: number
  pendingTestCases: number
  failedTestCases: number
  averageCoverage: number
  totalStories: number
}

function calculateDuration(embeddingTime: string | null, testCaseTime: string | null): string {
  if (!embeddingTime || !testCaseTime) return 'N/A';
  
  const embedding = new Date(embeddingTime);
  const testCase = new Date(testCaseTime);
  const diffMs = testCase.getTime() - embedding.getTime();
  
  // Convert to minutes and seconds
  const minutes = Math.floor(diffMs / 60000);
  const seconds = Math.floor((diffMs % 60000) / 1000);
  
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

function NextReloadBanner() {
  const [nextReload, setNextReload] = useState<Date | null>(null);
  const [timeLeft, setTimeLeft] = useState<string>("");

  useEffect(() => {
    const fetchNextReload = async () => {
      try {
        const response = await fetch("http://127.0.0.1:5000/api/stories/next-reload");
        const text = await response.text();
        const date = new Date(text.trim());
        if (!isNaN(date.getTime())) {
          setNextReload(date);
        }
      } catch (error) {
        console.error("Error fetching next reload time:", error);
      }
    };

    fetchNextReload();
  }, []);

  useEffect(() => {
    if (!nextReload) return;
    const interval = setInterval(() => {
      const now = new Date();
      const diff = Math.max(0, nextReload.getTime() - now.getTime());
      const hours = String(Math.floor(diff / 3600000)).padStart(2, '0');
      const minutes = String(Math.floor((diff % 3600000) / 60000)).padStart(2, '0');
      const seconds = String(Math.floor((diff % 60000) / 1000)).padStart(2, '0');
      setTimeLeft(`${hours}:${minutes}:${seconds}`);
    }, 1000);
    return () => clearInterval(interval);
  }, [nextReload]);

  return (
    <div className="w-full flex justify-center mb-4">
      <div className="flex items-center gap-2 bg-blue-100 border border-blue-300 text-blue-900 px-6 py-3 rounded-lg shadow font-semibold text-lg">
        <Clock className="w-5 h-5 text-blue-600" />
        {timeLeft ? (
          <>Next backend reload in <span className="font-mono">{timeLeft}</span></>
        ) : (
          "Loading next reload time..."
        )}
      </div>
    </div>
  );
}

function formatRagTestCases(testCases: any[]) {
  return testCases.map((tc, idx) => {
    return [
      `Test Case ${idx + 1}: ${tc.title}`,
      `Description: ${tc.description}`,
      `Steps:`,
      ...tc.steps.map((step: string, i: number) => `  ${i + 1}. ${step}`),
      `Expected Result: ${tc.expected_result}`,
      ''
    ].join('\n');
  }).join('\n');
}

function cleanAndParseLLMResponse(response: string) {
  // Remove triple backticks and ```json if present
  let cleaned = response.trim();
  if (cleaned.startsWith('```json')) cleaned = cleaned.slice(7);
  if (cleaned.startsWith('```')) cleaned = cleaned.slice(3);
  if (cleaned.endsWith('```')) cleaned = cleaned.slice(0, -3);
  cleaned = cleaned.trim();
  try {
    const parsed = JSON.parse(cleaned);
    return { parsed, cleaned };
  } catch {
    return { parsed: null, cleaned };
  }
}

export default function TestCaseGenerator() {
  const [formData, setFormData] = useState<FormData>({
    storyId: "",
    storyDescription: "",
    createdDate: "",
    fromDate: "",
    toDate: "",
  })

  const [showModal, setShowModal] = useState(false)
  const [showChatbot, setShowChatbot] = useState(false)
  const [chatMessage, setChatMessage] = useState("")
  const [selectedTestCases, setSelectedTestCases] = useState<string[]>([])
  const [searchPerformed, setSearchPerformed] = useState(false)
  const [activeTab, setActiveTab] = useState("dashboard")
  const [isLoading, setIsLoading] = useState(false)
  const [currentTime, setCurrentTime] = useState<string>('')
  const [chatMessages, setChatMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>([
    {
      role: "assistant",
      content:
        "Hello! I can help you generate test cases. Describe a feature or user story, and I'll create comprehensive test cases for you.",
    },
  ])
  const [isGenerating, setIsGenerating] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const [stories, setStories] = useState<Story[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [loading, setLoading] = useState(true)
  const [formattedDates, setFormattedDates] = useState<Record<string, string>>({})
  const router = useRouter()
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [perPage] = useState(10)
  const [dateFilter, setDateFilter] = useState<{from: string, to: string}>({from: '', to: ''});
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [selectedStory, setSelectedStory] = useState<Story | null>(null);
  const [showStoryContent, setShowStoryContent] = useState(false);
  const [lastReloadTime, setLastReloadTime] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<'gemini' | 'rag'>('gemini');
  const [chatbotWidth, setChatbotWidth] = useState(400);
  const [chatbotHeight, setChatbotHeight] = useState(500);
  const minWidth = 320;
  const minHeight = 350;
  const maxWidth = 700;
  const maxHeight = 800;
  const isResizing = useRef(false);
  const lastMousePosition = useRef({ x: 0, y: 0 });
  const [resizeDir, setResizeDir] = useState<string | null>(null);

  // Update time on mount and every second
  useEffect(() => {
    const updateTime = () => {
      setCurrentTime(new Date().toLocaleTimeString());
    };
    
    // Initial update
    updateTime();
    
    // Update every second
    const interval = setInterval(updateTime, 1000);
    
    // Cleanup
    return () => clearInterval(interval);
  }, []);

  // Fetch paginated stories from backend
  const fetchStories = async (page = 1, perPage = 10) => {
    setLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:5000/api/stories/?page=${page}&per_page=${perPage}`);
      const data = await res.json();
      setStories(data.stories || []);
      setTotalPages(data.total_pages || 1);
      setCurrentPage(data.current_page || 1);
      setLastReloadTime(data.last_reload_time);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStories(currentPage, perPage);
    // eslint-disable-next-line
  }, [currentPage, perPage]);

  // Debug: log stories and their timestamps
  useEffect(() => {
    console.debug('Fetched stories:', stories);
    stories.forEach((story, idx) => {
      console.debug(`Story[${idx}] id=${story.id} embedding_timestamp=`, story.embedding_timestamp, 'test_case_created_time=', story.test_case_created_time);
    });
  }, [stories]);

  // Format dates after component mounts
  useEffect(() => {
    const dates: Record<string, string> = {};
    stories.forEach(story => {
      if (story.created_on) {
        dates[story.id] = new Date(story.created_on).toLocaleString();
      }
    });
    setFormattedDates(dates);
  }, [stories]);

  // Search stories with advanced filtering
  const handleSearch = async () => {
    setLoading(true);

    // If ID is entered, filter by ID (exact match)
    if (formData.storyId.trim()) {
      let filtered = [...stories].filter((story: any) => story.id.toLowerCase() === formData.storyId.trim().toLowerCase());
      // Further filter by date range if set
      if (formData.fromDate || formData.toDate) {
        filtered = filtered.filter((story: any) => {
          if (!story.created_on) return false;
          const created = new Date(story.created_on);
          const from = formData.fromDate ? new Date(formData.fromDate) : null;
          const to = formData.toDate ? new Date(formData.toDate) : null;
          if (from && created < from) return false;
          if (to && created > to) return false;
          return true;
        });
      }
      setStories(filtered);
      setLoading(false);
      return;
    }

    // If description is entered, use similarity search
    if (formData.storyDescription.trim()) {
      try {
        const data = await api.searchStories(formData.storyDescription.trim(), 3); // fetch up to 3 similar stories
        let filtered = data.stories || [];
        // Further filter by date range if set
        if (formData.fromDate || formData.toDate) {
          filtered = filtered.filter((story: any) => {
            if (!story.created_on) return false;
            const created = new Date(story.created_on);
            const from = formData.fromDate ? new Date(formData.fromDate) : null;
            const to = formData.toDate ? new Date(formData.toDate) : null;
            if (from && created < from) return false;
            if (to && created > to) return false;
            return true;
          });
        }
        setStories(filtered);
      } catch (e) {
        setStories([]);
        toast.error('Failed to perform similarity search.');
      }
      setLoading(false);
      return;
    }

    // If only date range is set, filter all stories by date
    if (formData.fromDate || formData.toDate) {
      let filtered = [...stories].filter((story: any) => {
        if (!story.created_on) return false;
        const created = new Date(story.created_on);
        const from = formData.fromDate ? new Date(formData.fromDate) : null;
        const to = formData.toDate ? new Date(formData.toDate) : null;
        if (from && created < from) return false;
        if (to && created > to) return false;
        return true;
      });
      setStories(filtered);
      setLoading(false);
      return;
    }

    // If nothing is entered, fetch all stories
    fetchStories(currentPage, perPage);
    setLoading(false);
  };

  const handleInputChange = (field: keyof FormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  const openTestCasesModal = (count: number) => {
    const steps = []
    for (let i = 1; i <= count; i++) {
      steps.push(`Step ${i}: ${getRandomTestStep()}`)
    }
    setSelectedTestCases(steps)
    setShowModal(true)
  }

  const getRandomTestStep = () => {
    const steps = [
      "Open login page",
      "Enter valid credentials",
      "Click submit button",
      "Verify successful login",
      "Navigate to dashboard",
      "Check user profile",
      "Logout from application",
      "Verify error messages",
      "Test input validation",
      "Check responsive design",
    ]
    return steps[Math.floor(Math.random() * steps.length)]
  }

  const getUserSearchResult = (): TestCase => ({
    storyId: formData.storyId || "USER-001",
    storyDescription: formData.storyDescription || "User entered test case",
    testCaseCount: Math.floor(Math.random() * 10) + 1,
    processStartTime: new Date().toLocaleString(),
    processEndTime: new Date(Date.now() + 15 * 60000).toLocaleString(),
    testCaseCreatedTime: new Date(Date.now() + 20 * 60000).toLocaleString(),
  })

  const handleSendMessage = async () => {
    if (!chatMessage.trim() || isGenerating) return

    const userMessage = chatMessage.trim()
    setChatMessage("")
    setApiError(null)

    // Add user message to chat
    setChatMessages((prev) => [...prev, { role: "user", content: userMessage }])
    setIsGenerating(true)

    try {
      const response = await fetch("/api/generate-test-cases", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage,
          context: "Generate comprehensive test cases for the following feature or user story",
          model: selectedModel,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || "Failed to generate test cases")
      }

      if (data.error) {
        setApiError(data.error)
      }

      // If RAG, display structured test cases
      if (selectedModel === 'rag' && data.response) {
        const { parsed, cleaned } = cleanAndParseLLMResponse(data.response);
        console.log('RAG backend data.response:', data.response);
        console.log('RAG cleaned:', cleaned);
        console.log('RAG parsed:', parsed);
        if (parsed && Array.isArray(parsed)) {
          setChatMessages((prev) => [
            ...prev,
            { role: "assistant", content: formatRagTestCases(parsed) }
          ]);
        } else {
          setChatMessages((prev) => [
            ...prev,
            { role: "assistant", content: cleaned || '[No output from LLM]' }
          ]);
        }
      } else if (selectedModel === 'rag' && data.testCases) {
        setChatMessages((prev) => [...prev, { role: "assistant", content: formatRagTestCases(data.testCases) }])
      } else {
        setChatMessages((prev) => [...prev, { role: "assistant", content: data.response }])
      }
    } catch (error) {
      console.error("Error generating test cases:", error)
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I'm using mock test cases for demonstration. In production, you would connect to the Gemini API.",
        },
      ])
      setApiError("Using mock test cases. To use Gemini API, add GOOGLE_GENERATIVE_AI_API_KEY to your environment.")
    } finally {
      setIsGenerating(false)
    }
  }

  const handleDownload = async (storyId: string) => {
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/stories/testcases/download/${storyId}`);
      
      if (!response.ok) {
        throw new Error('Failed to download test cases');
      }

      // Get the blob from the response
      const blob = await response.blob();
      
      // Create a URL for the blob
      const url = window.URL.createObjectURL(blob);
      
      // Create a temporary link element
      const link = document.createElement('a');
      link.href = url;
      link.download = `test_cases_${storyId}.xlsx`;
      
      // Append to body, click, and remove
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Clean up the URL
      window.URL.revokeObjectURL(url);
      
      toast.success('Test cases downloaded successfully');
    } catch (error) {
      console.error('Error downloading test cases:', error);
      toast.error('Failed to download test cases');
    }
  };

  const handleDateFilter = async () => {
    setLoading(true);
    try {
      if (formData.storyDescription.trim()) {
        // Similarity search, then filter by date
        const data = await api.searchStories(formData.storyDescription.trim(), 3);
        let filtered = data.stories || [];
        if (dateFilter.from || dateFilter.to) {
          filtered = filtered.filter((story: any) => {
            if (!story.created_on) return false;
            const created = new Date(story.created_on);
            const from = dateFilter.from ? new Date(dateFilter.from) : null;
            const to = dateFilter.to ? new Date(dateFilter.to) : null;
            if (from && created < from) return false;
            if (to && created > to) return false;
            return true;
          });
        }
        setStories(filtered);
        setTotalPages(1);
        setCurrentPage(1);
      } else {
        // Paginated endpoint with date filter
        const data = await api.getStories(currentPage, perPage, dateFilter.from, dateFilter.to);
        setStories(data.stories || []);
        setTotalPages(data.total_pages || 1);
        setCurrentPage(data.current_page || 1);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleClearDateFilter = async () => {
    setDateFilter({from: '', to: ''});
    setFormData(prev => ({ ...prev, storyId: '', storyDescription: '' }));
    setLoading(true);
    try {
      const data = await api.getStories(currentPage, perPage);
      setStories(data.stories || []);
      setTotalPages(data.total_pages || 1);
      setCurrentPage(data.current_page || 1);
    } finally {
      setLoading(false);
    }
  };

  // Pagination controls
  const renderPagination = () => (
    <div className="flex justify-center items-center gap-2 mt-4">
      <Button
        variant="outline"
        size="sm"
        onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
        disabled={currentPage === 1}
        className="rounded"
      >
        <ChevronLeft className="h-4 w-4" />
      </Button>
      {Array.from({ length: totalPages }, (_, i) => (
        <Button
          key={i + 1}
          variant={currentPage === i + 1 ? "default" : "outline"}
          size="sm"
          onClick={() => setCurrentPage(i + 1)}
          className="rounded px-3"
        >
          {i + 1}
        </Button>
      ))}
      <Button
        variant="outline"
        size="sm"
        onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
        disabled={currentPage === totalPages}
        className="rounded"
      >
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  );

  const toggleRowExpand = (e: React.MouseEvent, storyId: string) => {
    e.stopPropagation();
    setExpandedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(storyId)) {
        newSet.delete(storyId);
      } else {
        newSet.add(storyId);
      }
      return newSet;
    });
  };

  const handleViewStoryContent = (e: React.MouseEvent, story: Story) => {
    e.stopPropagation();
    setSelectedStory(story);
    setShowStoryContent(true);
  };

  function handleResizeMouseDown(dir: string) {
    isResizing.current = true;
    setResizeDir(dir);
    document.body.style.userSelect = 'none';
  }

  useEffect(() => {
    function handleMouseMove(e: MouseEvent) {
      if (!isResizing.current || !resizeDir) return;
      if (resizeDir.includes('e')) {
        setChatbotWidth((w) => Math.max(minWidth, Math.min(maxWidth, w + e.movementX)));
      }
      if (resizeDir.includes('s')) {
        setChatbotHeight((h) => Math.max(minHeight, Math.min(maxHeight, h + e.movementY)));
      }
      if (resizeDir.includes('w')) {
        setChatbotWidth((w) => Math.max(minWidth, Math.min(maxWidth, w - e.movementX)));
      }
      if (resizeDir.includes('n')) {
        setChatbotHeight((h) => Math.max(minHeight, Math.min(maxHeight, h - e.movementY)));
      }
    }
    function handleMouseUp() {
      isResizing.current = false;
      setResizeDir(null);
      document.body.style.userSelect = '';
    }
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [resizeDir]);

  return (
    <div className="min-h-screen bg-gray-50 pt-32 px-4 flex flex-col font-sans">
      {/* Fixed Header */}
      <header className="fixed top-0 left-0 w-full z-50 bg-white shadow-sm border-b border-gray-300 px-4 md:px-8 py-4">
        <div className="flex justify-between items-center">
          {/* Logo in top left */}
          <div className="flex-shrink-0">
            <img src="/Logo-New.svg" alt="Innova Solutions" className="h-12 w-auto" />
          </div>

          {/* Main heading */}
          <div className="text-center">
            <h1 className="text-3xl font-bold text-blue-800">Test Case Generator</h1>
            <p className="text-sm text-blue-600 font-semibold mt-1">Powered by Gen AI</p>
          </div>

          {/* Right section with time, date, bell, and team */}
          <div className="flex-shrink-0 flex items-center space-x-4">
            {/* Time and Date */}
            <div className="text-right">
              <div className="text-lg font-bold text-slate-800">
                {currentTime || 'Loading...'}
              </div>
              <div className="text-sm text-slate-600">{new Date().toLocaleDateString()}</div>
            </div>

            {/* Bell notification icon */}
            <div className="relative">
              <div className="w-3 h-3 bg-red-400 rounded-full absolute -top-1 -right-1"></div>
              <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                <svg className="w-4 h-4 text-gray-600" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 2C8.13 2 6.6 3.53 6.6 5.4V9.8c0 .74-.4 1.42-1.05 1.79L4.2 12.4c-.65.37-1.05 1.05-1.05 1.79 0 1.16.94 2.1 2.1 2.1h9.5c1.16 0 2.1-.94 2.1-2.1 0-.74-.4-1.42-1.05-1.79l-1.35-.81c-.65-.37-1.05-1.05-1.05-1.79V5.4C13.4 3.53 11.87 2 10 2z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
            </div>

            {/* Team Delta */}
            <div className="bg-blue-500 text-white px-4 py-2 rounded-full flex items-center space-x-2">
              <div className="w-6 h-6 bg-white/20 rounded-full flex items-center justify-center">
                <Triangle className="h-3 w-3 fill-white" />
              </div>
              <div className="text-sm font-bold">
                <div className="text-xs opacity-90">Team</div>
                <div>DELTA</div>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="flex-grow">
        <div className="max-w-[95%] mx-auto mb-8">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-gray-900">User Stories</h1>
          </div>

          <Card className="shadow-lg border border-gray-200 rounded-xl overflow-hidden">
            <CardContent className="space-y-6 p-6 bg-white">
              {/* Search and Filter Section */}

              

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Story ID</label>
                <Input
                  placeholder="Enter Story ID"
                  value={formData.storyId}
                  onChange={(e) => handleInputChange("storyId", e.target.value)}
                  className="border-gray-300 focus:border-gray-400 focus:ring-gray-400 h-10 rounded-lg"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700">Story Description</label>
                <Textarea
                  placeholder="Enter story description..."
                  rows={3}
                  value={formData.storyDescription}
                  onChange={(e) => handleInputChange("storyDescription", e.target.value)}
                  className="border-gray-300 focus:border-gray-400 focus:ring-gray-400 resize-none rounded-lg"
                />
              </div>

              <div className="flex justify-start pt-4">
                <Button
                  onClick={handleSearch}
                  size="lg"
                  className="px-12 py-2 bg-blue-400 hover:bg-blue-500 text-white font-medium rounded-lg shadow-md"
                >
                  <Search className="mr-2 h-4 w-4" />
                  Search
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Date Filter Section */}
        <div className="max-w-[95%] mx-auto mb-4 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
  {/* Date filter controls - left side */}
  <div className="flex flex-col md:flex-row md:items-end gap-4">
    <div>
      <label className="text-sm font-medium text-slate-700">From Date</label>
      <Input
        type="date"
        value={dateFilter.from}
        onChange={e => setDateFilter(df => ({...df, from: e.target.value}))}
        className="border-gray-300 focus:border-gray-400 focus:ring-gray-400 h-10 rounded-lg"
      />
    </div>
    <div>
      <label className="text-sm font-medium text-slate-700">To Date</label>
      <Input
        type="date"
        value={dateFilter.to}
        onChange={e => setDateFilter(df => ({...df, to: e.target.value}))}
        className="border-gray-300 focus:border-gray-400 focus:ring-gray-400 h-10 rounded-lg"
      />
    </div>
    <Button
      onClick={handleDateFilter}
      className="bg-blue-400 hover:bg-blue-500 text-white font-medium rounded-lg shadow-md h-10 px-6 mt-6 md:mt-0"
    >
      Filter by Date
    </Button>
    <Button
      onClick={handleClearDateFilter}
      variant="outline"
      className="h-10 px-6 mt-6 md:mt-0 border-gray-300"
    >
      Clear Filter
    </Button>
  </div>
  {/* Timer - right side */}
  <div className="flex justify-end items-end w-full md:w-auto">
    <NextReloadBanner />
  </div>
</div>
        {/* Results Table Section */}
        <div className="max-w-[95%] mx-auto mb-12">
          <div className="flex items-center mb-4">
            <h2 className="text-xl font-semibold text-blue-800">Test Cases Results</h2>
          </div>
          <Card className="shadow-lg border border-gray-200 rounded-xl overflow-hidden">
            <CardContent className="p-0 bg-white">
              <div className="overflow-x-auto rounded-b-xl">
                {loading ? (
                  <div className="p-8 text-center text-blue-600 font-semibold">Loading...</div>
                ) : (
                  <Table className="rounded-xl overflow-hidden w-full">
                  <TableHeader>
                    <TableRow className="bg-blue-50 border-b border-gray-200">
                        <TableHead className="font-semibold text-blue-800 py-4 px-2 w-[10%]">Story ID</TableHead>
                        <TableHead className="font-semibold text-blue-800 py-4 px-2 w-[25%]">Story Description</TableHead>
                        <TableHead className="font-semibold text-blue-800 py-4 px-2 w-[25%]">Story Content</TableHead>
                        <TableHead className="font-semibold text-blue-800 py-4 px-2 w-[10%] text-center">No. of Test Cases</TableHead>
                        <TableHead className="font-semibold text-blue-800 py-4 px-2 w-[15%] text-center">Test Case Generated Time</TableHead>
                        <TableHead className="font-semibold text-blue-800 py-4 px-2 w-[10%] text-center">Duration</TableHead>
                        <TableHead className="font-semibold text-blue-800 py-4 px-2 w-[10%] text-center">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                      {stories.map((item, index) => (
                      <TableRow
                          key={item.id || index}
                          className={`hover:bg-gray-100 transition-colors`}
                        >
                          <TableCell className="font-medium text-slate-800 py-3 px-2">{item.id}</TableCell>
                          <TableCell className="text-slate-700 py-3 px-2">
                            <div className="space-y-2">
                              <div className="line-clamp-3 hover:line-clamp-none transition-all duration-200" title={item.description}>
                                {item.description}
                              </div>
                              <div className="inline-flex items-center gap-1 px-2 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-medium">
                                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                  <path d="M10 2a8 8 0 100 16 8 8 0 000-16zm0 14a6 6 0 110-12 6 6 0 010 12z"/>
                                </svg>
                                AI-generated description
                              </div>
                            </div>
                          </TableCell>
                          <TableCell className="px-6 py-4 text-sm text-gray-500">
                            {item.document_content ? (
                              <div>
                                <div className={`text-sm text-gray-700 ${!expandedRows.has(item.id) ? 'line-clamp-2' : ''}`}>
                                  {item.document_content}
                                </div>
                                {item.document_content.length > 150 && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      toggleRowExpand(e, item.id);
                                    }}
                                    className="mt-1 text-blue-600 hover:text-blue-800 hover:bg-blue-50"
                                  >
                                    {expandedRows.has(item.id) ? 'Show Less' : 'Read More'}
                                  </Button>
                                )}
                              </div>
                            ) : (
                              <span className="text-gray-400">No content available</span>
                            )}
                          </TableCell>
                          <TableCell className="py-3 px-2 text-center">
                            <Button
                              variant="ghost"
                              onClick={() => router.push(`/test-cases/${item.id}`)}
                              className="inline-flex items-center justify-center px-3 py-1 rounded-full bg-blue-50 text-blue-700 font-medium hover:bg-blue-100 transition-colors duration-200"
                            >
                              {item.test_case_count || 0} Test Cases
                            </Button>
                          </TableCell>
                          <TableCell className="py-3 px-2 text-center">
                            {item.test_case_created_time ? (
                              <div className="flex flex-col items-center text-sm">
                                <span className="text-gray-700">
                                  {new Date(item.test_case_created_time).toLocaleString('en-US', {
                                    year: 'numeric',
                                    month: 'short',
                                    day: 'numeric'
                                  })}
                                </span>
                                <span className="text-gray-500">
                                  {new Date(item.test_case_created_time).toLocaleString('en-US', {
                                    hour: '2-digit',
                                    minute: '2-digit',
                                    hour12: true
                                  })}
                                </span>
                              </div>
                            ) : (
                              <span className="text-gray-400">-</span>
                            )}
                          </TableCell>
                          <TableCell className="py-3 px-2 text-center">
                            {/* Duration column */}
                            <span className="text-sm">
                              {calculateDuration(item.embedding_timestamp, item.test_case_created_time)}
                            </span>
                          </TableCell>
                          <TableCell className="py-3 px-2 text-center">
                            <Button
                              variant="ghost"
                              onClick={() => handleDownload(item.id)}
                              className="inline-flex items-center justify-center px-3 py-1 rounded-full bg-green-50 text-green-700 font-medium hover:bg-green-100 transition-colors duration-200"
                            >
                              <Download className="h-4 w-4 mr-2" />
                              Download
                            </Button>
                          </TableCell>
                        </TableRow>
                    ))}
                  </TableBody>
                </Table>
                )}
                {renderPagination()}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Professional Footer */}
      <footer className="mt-auto">
        <div className="bg-blue-300 py-4 px-6 rounded-t-xl">
          <div className="max-w-7xl mx-auto flex justify-center items-center">
            <div className="flex space-x-4 mb-4 md:mb-0">
              <a href="#" className="text-blue-800 hover:text-blue-600 transition-colors">
                <Linkedin className="h-5 w-5" />
              </a>
              <a href="#" className="text-blue-800 hover:text-blue-600 transition-colors">
                <Facebook className="h-5 w-5" />
              </a>
              <a href="#" className="text-blue-800 hover:text-blue-600 transition-colors">
                <Twitter className="h-5 w-5" />
              </a>
              <a href="#" className="text-blue-800 hover:text-blue-600 transition-colors">
                <Instagram className="h-5 w-5" />
              </a>
              <a href="#" className="text-blue-800 hover:text-blue-600 transition-colors">
                <Youtube className="h-5 w-5" />
              </a>
              <a href="#" className="text-blue-800 hover:text-blue-600 transition-colors">
                <Music className="h-5 w-5" />
              </a>
            </div>
          </div>
        </div>
        <div className="bg-white py-3 text-center text-gray-600 text-sm">
          ©2025 Innova Solutions. All Rights Reserved.
        </div>
      </footer>

      {/* Modal Popup */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-w-2xl rounded-xl border border-gray-200">
          <DialogHeader className="bg-blue-100 text-blue-800 p-4 -m-6 mb-4 rounded-t-xl">
            <DialogTitle className="text-lg font-medium">Test Case Steps</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 max-h-96 overflow-y-auto px-2">
            {selectedTestCases.map((step, index) => (
              <div key={index} className="p-3 bg-gray-100 rounded-lg border-l-4 border-gray-400">
                <p className="text-sm font-medium text-slate-700">{step}</p>
              </div>
            ))}
          </div>
          <div className="flex justify-end pt-4">
            <Button
              onClick={() => setShowModal(false)}
              className="bg-blue-400 hover:bg-blue-500 text-white px-6 rounded-lg"
            >
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Fixed Chatbot */}
      <div
        className={!showChatbot ? "fixed bottom-6 right-6 z-50" : undefined}
        style={!showChatbot ? { width: 0, height: 0 } : undefined}
      >
        {!showChatbot ? (
          <Button
            onClick={() => setShowChatbot(true)}
            size="lg"
            className="rounded-full h-12 w-12 shadow-lg hover:shadow-xl transition-all duration-300 bg-blue-400 hover:bg-blue-500 fixed bottom-6 right-6 z-50"
          >
            <MessageCircle className="h-5 w-5" />
          </Button>
        ) : (
          <div
            className="fixed bottom-6 right-6 z-50 flex flex-col h-full bg-white border border-gray-300 rounded-2xl shadow-2xl overflow-hidden"
            style={{ width: chatbotWidth, height: chatbotHeight, minWidth, minHeight, maxWidth, maxHeight, boxShadow: '0 8px 32px rgba(0,0,0,0.18)' }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3 bg-gradient-to-r from-blue-100 to-blue-200 border-b border-gray-200">
              <span className="font-semibold text-blue-800 text-base">AI Test Case Assistant</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowChatbot(false)}
                className="text-gray-500 hover:bg-gray-200 rounded-full"
              >
                <X className="h-5 w-5" />
              </Button>
            </div>
            {/* Chat area */}
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 bg-gradient-to-br from-white to-blue-50" style={{scrollbarWidth:'thin'}}>
              {chatMessages.map((message, index) => {
                console.log('Chat message content:', message.content);
                return (
                  <div key={index} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div
                      className={
                        message.role === "user"
                          ? "bg-blue-500 text-white rounded-2xl rounded-br-sm px-4 py-2 max-w-[80%] shadow"
                          : "bg-gray-100 text-gray-800 rounded-2xl rounded-bl-sm px-4 py-2 max-w-[80%] shadow border border-blue-100"
                      }
                      style={{ wordBreak: 'break-word', whiteSpace: 'pre-wrap' }}
                    >
                      {message.role === "assistant" ? (
                        <pre className="text-sm whitespace-pre-wrap" style={{background:'none',margin:0,padding:0,border:'none'}}>
                          {message.content && message.content.toString().trim() ? message.content : '[No output from LLM]'}
                        </pre>
                      ) : (
                        <span className="text-sm whitespace-pre-wrap">{message.content}</span>
                      )}
                    </div>
                  </div>
                );
              })}
              {isGenerating && (
                <div className="flex justify-start">
                  <div className="inline-block p-2 rounded-lg bg-white border border-gray-200 text-slate-500 text-sm shadow">Generating test cases...</div>
                </div>
              )}
            </div>
            {/* Input area */}
            <div className="px-4 py-3 bg-white border-t border-gray-200 flex flex-col gap-2">
              <div className="flex space-x-2 mb-1 items-center">
                <label className="text-xs font-medium text-gray-700">Model:</label>
                <select
                  value={selectedModel}
                  onChange={e => setSelectedModel(e.target.value as 'gemini' | 'rag')}
                  className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-blue-200"
                >
                  <option value="gemini">Gemini</option>
                  <option value="rag">RAG</option>
                </select>
              </div>
              <div className="flex space-x-2 items-center">
                <Input
                  placeholder="Describe your feature for test case generation..."
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && !isGenerating && handleSendMessage()}
                  disabled={isGenerating}
                  className="border-gray-300 focus:border-gray-400 focus:ring-gray-400 rounded-lg flex-1 text-sm"
                />
                <Button
                  size="sm"
                  onClick={handleSendMessage}
                  disabled={isGenerating || !chatMessage.trim()}
                  className="bg-blue-400 hover:bg-blue-500 text-white rounded-lg px-4 py-2 text-sm"
                >
                  Send
                </Button>
              </div>
            </div>
            {/* Resize handles: corners and sides */}
            {/* Corners */}
            <div onMouseDown={() => handleResizeMouseDown('nw')} className="absolute top-0 left-0 w-3 h-3 cursor-nwse-resize z-10" />
            <div onMouseDown={() => handleResizeMouseDown('ne')} className="absolute top-0 right-0 w-3 h-3 cursor-nesw-resize z-10" />
            <div onMouseDown={() => handleResizeMouseDown('sw')} className="absolute bottom-0 left-0 w-3 h-3 cursor-nesw-resize z-10" />
            <div onMouseDown={() => handleResizeMouseDown('se')} className="absolute bottom-0 right-0 w-3 h-3 cursor-nwse-resize z-10" />
            {/* Sides */}
            <div onMouseDown={() => handleResizeMouseDown('n')} className="absolute top-0 left-3 right-3 h-2 cursor-ns-resize z-10" />
            <div onMouseDown={() => handleResizeMouseDown('s')} className="absolute bottom-0 left-3 right-3 h-2 cursor-ns-resize z-10" />
            <div onMouseDown={() => handleResizeMouseDown('e')} className="absolute top-3 bottom-3 right-0 w-2 cursor-ew-resize z-10" />
            <div onMouseDown={() => handleResizeMouseDown('w')} className="absolute top-3 bottom-3 left-0 w-2 cursor-ew-resize z-10" />
          </div>
        )}
      </div>

      {/* Story Content Dialog */}
      <Dialog open={showStoryContent} onOpenChange={setShowStoryContent}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold text-blue-800">
              Story Content
            </DialogTitle>
            <DialogDescription className="text-sm text-gray-600">
              ID: {selectedStory?.id}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Story Title</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-gray-700 font-medium">{selectedStory?.title}</p>
              </div>
            </div>
            
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Story Summary</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-gray-700">{selectedStory?.summary}</p>
              </div>
            </div>
            
            {selectedStory?.doc_content_text && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Story Content</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-gray-700 whitespace-pre-wrap">{selectedStory.doc_content_text}</p>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
