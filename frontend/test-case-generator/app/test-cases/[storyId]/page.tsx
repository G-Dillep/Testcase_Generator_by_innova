"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, TestCase, TestCaseResponse } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp, Download, ArrowLeft, Info, CheckCircle2, AlertCircle, Brain, Triangle, Eye, FileText } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

export default function StoryTestCasesPage() {
  const params = useParams();
  const router = useRouter();
  const storyId = typeof params?.storyId === 'string' ? params.storyId : Array.isArray(params?.storyId) ? params.storyId[0] : '';
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [storyDescription, setStoryDescription] = useState<string | null>(null);
  const [storyContent, setStoryContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState<string>("");
  const [selectedTestCase, setSelectedTestCase] = useState<TestCase | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [showStoryContent, setShowStoryContent] = useState(false);
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await api.getTestCases(storyId);
        setTestCases(response.testcases);
        setStoryDescription(response.storyDescription);
        // Fetch story content
        const storyResponse = await fetch(`http://127.0.0.1:5000/api/stories/${storyId}`);
        if (storyResponse.ok) {
          const storyData = await storyResponse.json();
          console.log('Story data response:', storyData); // Debug log
          setStoryContent(storyData.document_content);
        } else {
          console.error('Failed to fetch story:', storyResponse.status);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch test cases');
      } finally {
        setLoading(false);
      }
    };

    if (storyId) {
      fetchData();
    }
  }, [storyId]);

  useEffect(() => {
    const updateTime = () => {
      setCurrentTime(new Date().toLocaleTimeString());
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleViewDetails = (testCase: TestCase) => {
    setSelectedTestCase(testCase);
    setIsDialogOpen(true);
  };

  const handleDownload = async () => {
    try {
      const response = await fetch(`http://127.0.0.1:5000/api/stories/testcases/download/${storyId}`);
      if (!response.ok) throw new Error('Download failed');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `test_cases_${storyId}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download error:', error);
    }
  };

  const toggleCardExpand = (e: React.MouseEvent, cardId: string) => {
    e.stopPropagation();
    setExpandedCards(prev => {
      const newSet = new Set(prev);
      if (newSet.has(cardId)) {
        newSet.delete(cardId);
      } else {
        newSet.add(cardId);
      }
      return newSet;
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="fixed top-0 left-0 w-full z-50 bg-white shadow-sm border-b border-gray-300 px-4 md:px-8 py-4">
        <div className="flex justify-between items-center">
          <div className="flex-shrink-0">
            <img src="/Logo-New.svg" alt="Innova Solutions" className="h-12 w-auto" />
          </div>
          <div className="text-center">
            <h1 className="text-3xl font-bold text-blue-800">Test Case Generator</h1>
            <p className="text-sm text-blue-600 font-semibold mt-1">Powered by Gen AI</p>
          </div>
          <div className="flex-shrink-0 flex items-center space-x-4">
            <div className="text-right">
              <div className="text-lg font-bold text-slate-800">
                {currentTime || 'Loading...'}
              </div>
              <div className="text-sm text-slate-600">{new Date().toLocaleDateString()}</div>
            </div>
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

      <div className="max-w-[95%] mx-auto py-8 pt-32">
        <Card className="shadow-lg border border-gray-200 rounded-xl overflow-hidden">
          <CardHeader className="bg-gradient-to-r from-blue-50 to-white border-b border-gray-200">
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <Button
                    variant="outline"
                    onClick={() => router.back()}
                    className="flex items-center gap-2 border-gray-300 hover:bg-white hover:border-blue-300 transition-colors"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Back to Stories
                  </Button>
                  <div className="h-6 w-px bg-gray-300"></div>
                  <div className="flex items-center gap-2">
                    <div className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium flex items-center gap-1">
                      <CheckCircle2 className="h-4 w-4" />
                      {testCases.length} Test Cases
                    </div>
                    <div className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-medium flex items-center gap-1">
                      <Brain className="h-4 w-4" />
                      AI Generated
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setShowStoryContent(true)}
                    className="flex items-center gap-2 border-gray-300 hover:bg-white hover:border-blue-300 transition-colors"
                  >
                    <FileText className="h-4 w-4" />
                    View Story Content
                  </Button>
                  <Button
                    variant="outline"
                    onClick={handleDownload}
                    className="flex items-center gap-2 border-gray-300 hover:bg-white hover:border-blue-300 transition-colors"
                  >
                    <Download className="h-4 w-4" />
                    Download Test Cases
                  </Button>
                </div>
              </div>
              
              <div className="mt-2">
                <CardTitle className="text-xl font-semibold text-blue-800 mb-3">
                  Test Cases for Story {storyId}
                </CardTitle>
                {storyDescription && (
                  <p className="text-gray-700 text-sm leading-relaxed">
                    {storyDescription}
                  </p>
                )}
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-0 bg-white">
            {loading ? (
              <div className="p-8 text-center text-blue-600 font-semibold">Loading...</div>
            ) : error ? (
              <div className="p-8 text-center text-red-600 font-semibold">{error}</div>
            ) : testCases.length === 0 ? (
              <div className="p-8 text-center text-gray-600">No test cases found for this story.</div>
            ) : (
              <div className="grid grid-cols-2 gap-6 p-6">
                {testCases.map((tc, idx) => (
                  <Card 
                    key={tc.test_case_id || tc.id || idx} 
                    className="border rounded-lg overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => handleViewDetails(tc)}
                  >
                    <div className="p-4 bg-gray-50 border-b">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-800 font-semibold">
                            {idx + 1}
                          </div>
                          <div>
                            <div className="font-semibold text-blue-800">{tc.title}</div>
                            <div className="text-gray-600 text-sm">
                              ID: <span className="font-mono">{tc.test_case_id || tc.id || "N/A"}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            tc.priority === 'high' ? 'bg-red-100 text-red-800' :
                            tc.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-green-100 text-green-800'
                          }`}>
                            {tc.priority || 'low'} priority
                          </span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleViewDetails(tc);
                            }}
                            className="text-blue-600 hover:text-blue-800 hover:bg-blue-50"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Story Content Dialog */}
      <Dialog open={showStoryContent} onOpenChange={setShowStoryContent}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold text-blue-800">
              Story Content
            </DialogTitle>
            <DialogDescription className="text-sm text-gray-600">
              ID: {storyId}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Story Description</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-gray-700">{storyDescription}</p>
              </div>
            </div>
            
            {storyContent && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Story Content</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-gray-700 whitespace-pre-wrap">{storyContent}</p>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Test Case Details Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold text-blue-800">
              {selectedTestCase?.title}
            </DialogTitle>
            <DialogDescription className="text-sm text-gray-600">
              ID: {selectedTestCase?.test_case_id || selectedTestCase?.id || "N/A"}
            </DialogDescription>
          </DialogHeader>
          
          {selectedTestCase && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-2">Test Steps</h3>
                    <div className="space-y-2">
                      {selectedTestCase.steps?.map((step, stepIdx) => (
                        <div key={stepIdx} className="flex gap-3 p-3 bg-gray-50 rounded-lg">
                          <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center text-blue-800 font-semibold flex-shrink-0">
                            {stepIdx + 1}
                          </div>
                          <div className="text-sm text-gray-700">{step}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-2">Expected Results</h3>
                    <div className="space-y-2">
                      {selectedTestCase?.expected_results ? (
                        // Multiple expected results
                        selectedTestCase.expected_results.map((result, resultIdx) => (
                          <div key={resultIdx} className="flex gap-3 p-3 bg-gray-50 rounded-lg">
                            <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center text-green-800 font-semibold flex-shrink-0">
                              {resultIdx + 1}
                            </div>
                            <div className="text-sm text-gray-700">{result}</div>
                          </div>
                        ))
                      ) : selectedTestCase?.expected_result ? (
                        // Single expected result
                        <div className="flex gap-3 p-3 bg-gray-50 rounded-lg">
                          <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center text-green-800 font-semibold flex-shrink-0">
                            1
                          </div>
                          <div className="text-sm text-gray-700">{selectedTestCase.expected_result}</div>
                        </div>
                      ) : (
                        <div className="text-sm text-gray-500 italic">No expected results defined</div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">Priority:</span>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      selectedTestCase.priority === 'high' ? 'bg-red-100 text-red-800' :
                      selectedTestCase.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-green-100 text-green-800'
                    }`}>
                      {selectedTestCase.priority || 'low'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">Generated by:</span>
                    <span className="px-2 py-1 rounded text-xs font-medium bg-purple-100 text-purple-800 flex items-center gap-1">
                      <Brain className="h-3 w-3" />
                      AI
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
} 