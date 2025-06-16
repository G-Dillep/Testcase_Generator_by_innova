"use client"

import { useState, useEffect } from "react"
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
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useRouter } from "next/navigation"
import { api, Story } from "@/lib/api"
import { toast } from "sonner"

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
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStories(currentPage, perPage);
    // eslint-disable-next-line
  }, [currentPage, perPage]);

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
    let filtered = [...stories];

    // Filter by ID if entered
    if (formData.storyId.trim()) {
      filtered = filtered.filter(story => story.id.toLowerCase() === formData.storyId.trim().toLowerCase());
    }

    // Filter by description if entered
    if (formData.storyDescription.trim()) {
      filtered = filtered.filter(story =>
        story.description && story.description.toLowerCase().includes(formData.storyDescription.trim().toLowerCase())
      );
    }

    // Filter by date range if from/to dates are set
    if (formData.fromDate || formData.toDate) {
      filtered = filtered.filter(story => {
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
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || "Failed to generate test cases")
      }

      // Check if there's an error message but we still got a response (fallback case)
      if (data.error) {
        setApiError(data.error)
      }

      // Add AI response to chat
      setChatMessages((prev) => [...prev, { role: "assistant", content: data.response }])
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
        {/* Input Form Section */}
        <div className="max-w-[95%] mx-auto mb-8">
          <div className="flex items-center mb-4">
            <h2 className="text-xl font-semibold text-blue-800">User Stories</h2>
          </div>

          <Card className="shadow-lg border border-gray-200 rounded-xl overflow-hidden">
            <CardContent className="space-y-6 p-6 bg-white">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                  <label className="text-sm font-medium text-slate-700">Created Date</label>
                  <Input
                    type="date"
                    value={formData.createdDate}
                    onChange={(e) => handleInputChange("createdDate", e.target.value)}
                    className="border-gray-300 focus:border-gray-400 focus:ring-gray-400 h-10 rounded-lg"
                  />
                </div>
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

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">From Date</label>
                  <Input
                    type="date"
                    value={formData.fromDate}
                    onChange={(e) => handleInputChange("fromDate", e.target.value)}
                    className="border-gray-300 focus:border-gray-400 focus:ring-gray-400 h-10 rounded-lg"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700">To Date</label>
                  <Input
                    type="date"
                    value={formData.toDate}
                    onChange={(e) => handleInputChange("toDate", e.target.value)}
                    className="border-gray-300 focus:border-gray-400 focus:ring-gray-400 h-10 rounded-lg"
                  />
                </div>
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
                        <TableHead className="font-semibold text-blue-800 py-4 px-2 w-[40%]">Story Description</TableHead>
                        <TableHead className="font-semibold text-blue-800 py-4 px-2 w-[15%] text-center">No. of Test Cases</TableHead>
                        <TableHead className="font-semibold text-blue-800 py-4 px-2 w-[20%] text-center">Test Case Generated Time</TableHead>
                        <TableHead className="font-semibold text-blue-800 py-4 px-2 w-[15%] text-center">Action</TableHead>
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
                            <div className="line-clamp-3 hover:line-clamp-none transition-all duration-200" title={item.description}>{item.description}</div>
                          </TableCell>
                          <TableCell className="py-3 px-2 text-center">
                            <Button
                              variant="link"
                              onClick={() => router.push(`/test-cases/${item.id}`)}
                              className="text-gray-600 hover:text-gray-700 p-0 font-medium"
                            >
                              <Eye className="mr-1 h-4 w-4" />
                              {item.num_test_cases} test cases
                            </Button>
                          </TableCell>
                          <TableCell className="py-3 px-2 text-center">
                            {item.created_on ? (
                              <span className="whitespace-nowrap">{formattedDates[item.id] || '-'}</span>
                            ) : (
                              <span className="text-gray-400">-</span>
                            )}
                          </TableCell>
                          <TableCell className="py-3 px-2 text-center">
                            <div className="flex items-center justify-center gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleDownload(item.id)}
                                className="border-gray-300 text-slate-700 hover:bg-blue-400 hover:text-white hover:border-blue-400 rounded-lg p-1 w-8 h-8 flex items-center justify-center"
                              >
                                <Download className="h-4 w-4" />
                              </Button>
                              <span className="text-xs text-gray-500">Download</span>
                            </div>
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
      <div className="fixed bottom-6 right-6 z-50">
        {!showChatbot ? (
          <Button
            onClick={() => setShowChatbot(true)}
            size="lg"
            className="rounded-full h-12 w-12 shadow-lg hover:shadow-xl transition-all duration-300 bg-blue-400 hover:bg-blue-500"
          >
            <MessageCircle className="h-5 w-5" />
          </Button>
        ) : (
          <Card className="w-96 shadow-lg border border-gray-200 rounded-xl overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 bg-blue-100 text-blue-800">
              <CardTitle className="text-sm font-medium">AI Test Case Assistant</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowChatbot(false)}
                className="text-white hover:bg-gray-500"
              >
                <X className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent className="space-y-4 p-4 bg-white">
              {apiError && (
                <Alert variant="default" className="bg-gray-50 border-gray-200 text-gray-800 text-xs">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{apiError}</AlertDescription>
                </Alert>
              )}

              <div className="h-64 bg-gray-100 rounded-lg p-3 overflow-y-auto border border-gray-200">
                {chatMessages.map((message, index) => (
                  <div key={index} className={`mb-3 ${message.role === "user" ? "text-right" : "text-left"}`}>
                    <div
                      className={`inline-block p-2 rounded-lg max-w-xs ${
                        message.role === "user"
                          ? "bg-gray-400 text-white"
                          : "bg-white border border-gray-200 text-slate-700"
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    </div>
                  </div>
                ))}
                {isGenerating && (
                  <div className="text-left mb-3">
                    <div className="inline-block p-2 rounded-lg bg-white border border-gray-200">
                      <p className="text-sm text-slate-500">Generating test cases...</p>
                    </div>
                  </div>
                )}
              </div>
              <div className="flex space-x-2">
                <Input
                  placeholder="Describe your feature for test case generation..."
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && !isGenerating && handleSendMessage()}
                  disabled={isGenerating}
                  className="border-gray-300 focus:border-gray-400 focus:ring-gray-400 rounded-lg"
                />
                <Button
                  size="sm"
                  onClick={handleSendMessage}
                  disabled={isGenerating || !chatMessage.trim()}
                  className="bg-blue-400 hover:bg-blue-500 text-white rounded-lg"
                >
                  Send
                </Button>
              </div>
            </CardContent>
            <CardFooter className="bg-gray-50 p-2 text-xs text-slate-500 border-t border-gray-200">
              <p>
                Demo Mode: Using mock test cases. For production, add GOOGLE_GENERATIVE_AI_API_KEY to your environment.
              </p>
            </CardFooter>
          </Card>
        )}
      </div>
    </div>
  )
}
