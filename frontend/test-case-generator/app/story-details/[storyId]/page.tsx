"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp, Download, ArrowLeft, Info, CheckCircle2, AlertCircle, Brain, Triangle, Eye, FileText } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

interface ImpactedTestCase {
  id: string;
  title: string;
  description: string;
  original_story_id: string;
  new_story_id: string;
  similarity_score: number;
  status: string;
  priority: 'high' | 'medium' | 'low';
  severity: 'high' | 'medium' | 'low';
  steps: string[];
  expected_result: string;
  modified_test_case_id: string;
  original_steps?: string[];
  original_expected_result?: string;
  original_title: string;
  original_test_case_id: string;
  modified_date?: string;
}

export default function StoryImpactAnalysisPage() {
  const params = useParams();
  const router = useRouter();
  const storyId = typeof params?.storyId === 'string' ? params.storyId : Array.isArray(params?.storyId) ? params.storyId[0] : '';
  const [impactedTestCases, setImpactedTestCases] = useState<ImpactedTestCase[]>([]);
  const [storyDescription, setStoryDescription] = useState<string | null>(null);
  const [storyContent, setStoryContent] = useState<string | null>(null);
  const [storyProject, setStoryProject] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingOriginal, setLoadingOriginal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState<string>("");
  const [selectedTestCase, setSelectedTestCase] = useState<ImpactedTestCase | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [showStoryContent, setShowStoryContent] = useState(false);
  const [showOriginalTestCase, setShowOriginalTestCase] = useState(false);
  const [showFullContent, setShowFullContent] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Fetch impacted test cases
        const response = await fetch(`http://127.0.0.1:5000/api/stories/impacts/story/${storyId}`);
        if (!response.ok) throw new Error('Failed to fetch impacted test cases');
        const data = await response.json();
        
        // Extract all modified test cases from impacts
        const allModifiedTestCases = [...(data.caused_impacts || []), ...(data.received_impacts || [])].map(impact => {
          let analysisDetails = {};
          try {
            if (impact.impact_analysis_json) {
              analysisDetails = typeof impact.impact_analysis_json === 'string' 
                ? JSON.parse(impact.impact_analysis_json)
                : impact.impact_analysis_json;
            }
          } catch (e) {
            console.error('Error parsing impact analysis JSON:', e);
          }

          // Get the modified test case details
          const modifiedTestCase = analysisDetails.modified_test_case || {};
          
          console.log('Impact Data:', {
            original_test_case_id: impact.original_test_case_id,
            original_story_id: impact.original_story_id,
            analysisDetails
          });
          
          return {
            id: impact.modified_test_case_id || `${impact.original_test_case_id}-MOD` || impact.impact_id,
            title: modifiedTestCase.title || analysisDetails.title || impact.title || 'Modified Test Case',
            original_story_id: impact.original_story_id,
            original_test_case_id: impact.original_test_case_id || analysisDetails.original_test_case_id,
            modified_test_case_id: impact.modified_test_case_id || modifiedTestCase.id || `${impact.original_test_case_id}-MOD`,
            similarity_score: impact.similarity_score,
            steps: modifiedTestCase.steps || [],
            expected_result: modifiedTestCase.expected_result || '',
            priority: modifiedTestCase.priority || 'medium',
            severity: modifiedTestCase.severity || analysisDetails.severity || 'medium',
            description: impact.impacted_story_description || impact.new_story_description || '',
            new_story_id: impact.new_story_id,
            status: 'active',
            original_steps: [],
            original_expected_result: '',
            original_title: '',
            modified_date: impact.modified_date,
            fullPageContent: '',
            pageNumber: 0
          };
        });
        
        console.log('Processed Test Cases:', allModifiedTestCases); // Log final processed data
        
        setImpactedTestCases(allModifiedTestCases);
        
        // Fetch story details
        const storyResponse = await fetch(`http://127.0.0.1:5000/api/stories/${storyId}`);
        if (storyResponse.ok) {
          const storyData = await storyResponse.json();
          setStoryDescription(storyData.description);
          setStoryContent(storyData.document_content);
          setStoryProject(storyData.project_id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch impact analysis');
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

  const handleViewDetails = (testCase: ImpactedTestCase) => {
    setSelectedTestCase(testCase);
    setIsDialogOpen(true);
  };

  // Function to fetch original test case details
  const fetchOriginalTestCase = async (testCase: ImpactedTestCase) => {
    try {
      setLoadingOriginal(true);
      console.log('Fetching original test case:', {
        original_test_case_id: testCase.original_test_case_id,
        original_story_id: testCase.original_story_id
      });
      
      // Updated endpoint to include story ID
      const response = await fetch(`http://127.0.0.1:5000/api/stories/${testCase.original_story_id}/test-cases/${testCase.original_test_case_id}`);
      if (!response.ok) throw new Error('Failed to fetch original test case');
      const data = await response.json();
      
      console.log('Original test case data:', data);

      // Update the selected test case with original data
      setSelectedTestCase(prev => prev ? {
        ...prev,
        original_steps: data.test_steps || data.steps || [],
        original_expected_result: data.expected_result || '',
        original_title: data.title || data.test_title || ''
      } : null);
    } catch (err) {
      console.error('Error fetching original test case:', err);
    } finally {
      setLoadingOriginal(false);
    }
  };

  // Add effect to fetch original test case when showing it
  useEffect(() => {
    if (showOriginalTestCase && selectedTestCase?.original_test_case_id) {
      fetchOriginalTestCase(selectedTestCase);
    }
  }, [showOriginalTestCase]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="fixed top-0 left-0 w-full z-50 bg-background shadow-sm border-b border-border px-4 md:px-8 py-4">
        <div className="flex justify-between items-center">
          <div className="flex-shrink-0">
            <img src="/Logo-New.svg" alt="Innova Solutions" className="h-12 w-auto" />
          </div>
          <div className="text-center">
            <h1 className="text-3xl font-bold text-primary">Impact Analysis</h1>
            <p className="text-sm text-muted-foreground font-semibold mt-1">Powered by Gen AI</p>
          </div>
          <div className="flex-shrink-0 flex items-center space-x-4">
            <div className="text-right">
              <div className="text-lg font-bold text-foreground">
                {currentTime || 'Loading...'}
              </div>
              <div className="text-sm text-muted-foreground">{new Date().toLocaleDateString()}</div>
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

      {/* Main Content */}
      <div className="max-w-[95%] mx-auto py-8 pt-32">
        <Card className="shadow-lg border border-border rounded-xl overflow-hidden">
          <CardHeader className="bg-gradient-to-r from-muted/50 to-background border-b border-border">
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <Button
                    variant="outline"
                    onClick={() => router.back()}
                    className="flex items-center gap-2 border-border hover:bg-muted transition-colors"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Back to Stories
                  </Button>
                  <div className="h-6 w-px bg-border"></div>
                  <div className="flex items-center gap-2">
                    <div className="px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-sm font-medium flex items-center gap-1">
                      <CheckCircle2 className="h-4 w-4" />
                      {impactedTestCases.length} Impacted Test Cases
                    </div>
                    <div className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-medium flex items-center gap-1">
                      <Brain className="h-4 w-4" />
                      Impact Analysis by AI
                    </div>
                    {storyProject && (
                      <div className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium flex items-center gap-1">
                        <FileText className="h-4 w-4" />
                        Project: {storyProject}
                      </div>
                    )}
                  </div>
                </div>
                <Button
                  variant="outline"
                  onClick={() => setShowStoryContent(true)}
                  className="flex items-center gap-2 border-border hover:bg-muted transition-colors"
                >
                  <FileText className="h-4 w-4" />
                  View Story Content
                </Button>
              </div>
              
              <div className="mt-2">
                <CardTitle className="text-xl font-semibold text-primary mb-3">
                  Impact Analysis for Story {storyId}
                </CardTitle>
                {storyDescription && (
                  <p className="text-foreground text-sm leading-relaxed">
                    {storyDescription}
                  </p>
                )}
              </div>
            </div>
          </CardHeader>

          <CardContent>
            {loading ? (
              <div className="p-8 text-center text-blue-600 font-semibold">Loading...</div>
            ) : error ? (
              <div className="p-8 text-center text-red-600 font-semibold">{error}</div>
            ) : impactedTestCases.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">No impacted test cases found for this story.</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-6">
                {impactedTestCases.map((testCase, idx) => (
                  <Card 
                    key={testCase.id || idx}
                    className="border border-border hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => handleViewDetails(testCase)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3">
                        <div className="w-8 h-8 bg-amber-100 rounded-full flex items-center justify-center text-amber-800 font-semibold flex-shrink-0">
                          {idx + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          {/* Title */}
                          <div className="font-medium text-foreground text-base break-words mb-2">
                            {testCase.title}
                          </div>
                          {/* Test Case ID */}
                          <div className="text-sm text-muted-foreground">
                            <span className="font-medium">ID: </span>
                            <span className="font-mono bg-muted/50 px-2 py-0.5 rounded">
                              {testCase.modified_test_case_id}
                            </span>
                          </div>
                        </div>
                      </div>
                    </CardContent>
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
            <DialogTitle className="text-xl font-semibold text-primary">
              Story Content
            </DialogTitle>
            <DialogDescription className="text-sm text-muted-foreground">
              ID: {storyId}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-2">Story Description</h3>
              <div className="bg-muted rounded-lg p-4">
                <p className="text-foreground">{storyDescription}</p>
              </div>
            </div>
            
            {storyContent && (
              <div>
                <h3 className="text-sm font-semibold text-foreground mb-2">Story Content</h3>
                <div className="bg-muted rounded-lg p-4">
                  <p className="text-foreground whitespace-pre-wrap">{storyContent}</p>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Full Content Dialog */}
      <Dialog open={showFullContent} onOpenChange={setShowFullContent}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold text-purple-600 flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Page {selectedTestCase?.pageNumber} Content
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="bg-purple-50 rounded-lg p-6 border border-purple-100">
              <p className="text-foreground whitespace-pre-wrap">
                {selectedTestCase?.fullPageContent}
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Test Case Details Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold text-blue-600 flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Test Case Details
            </DialogTitle>
            <DialogDescription className="text-sm text-muted-foreground font-mono">
              ID: {selectedTestCase?.modified_test_case_id || 'N/A'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6 py-4">
            {/* Title */}
            <div className="space-y-2">
              <div className="text-sm font-medium text-blue-600">Title</div>
              <p className="text-base bg-blue-50 p-3 rounded-lg">{selectedTestCase?.title || 'N/A'}</p>
            </div>

            {/* Story References */}
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {/* Left Column: Original IDs */}
                <div className="space-y-2">
                  <div>
                    <div className="text-sm font-medium text-purple-600">Original Story ID</div>
                    <div className="font-mono bg-purple-50 p-2 rounded-lg mt-1 border border-purple-100">
                      {selectedTestCase?.original_story_id || 'N/A'}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-purple-600">Original Test Case ID</div>
                    <div className="font-mono bg-purple-50 p-2 rounded-lg mt-1 border border-purple-100">
                      {selectedTestCase?.original_test_case_id || 'N/A'}
                    </div>
                  </div>
                </div>
                {/* Right Column: New Story ID and View Button */}
                <div className="space-y-2">
                  <div>
                    <div className="text-sm font-medium text-emerald-600">New Story ID</div>
                    <div className="font-mono bg-emerald-50 p-2 rounded-lg mt-1 border border-emerald-100">
                      {selectedTestCase?.new_story_id || 'N/A'}
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    className="w-full mt-1 group relative flex items-center justify-center gap-2 overflow-hidden bg-white transition-all hover:bg-blue-50 border-blue-200 text-blue-600 hover:border-blue-300"
                    onClick={() => setShowOriginalTestCase(prev => !prev)}
                  >
                    <Eye className="h-4 w-4" />
                    {showOriginalTestCase ? 'Hide Original' : 'View Original'}
                  </Button>
                </div>
              </div>

              {/* Original Test Case Section - Moved here */}
              {showOriginalTestCase && (
                <div className="space-y-4 border border-dashed border-blue-200 bg-gradient-to-br from-blue-50/50 to-purple-50/50 p-4 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 text-blue-600">
                      <FileText className="h-4 w-4" />
                      <h3 className="font-medium">Original Test Case</h3>
                    </div>
                    {selectedTestCase?.original_title && (
                      <div className="text-sm text-blue-600">
                        {selectedTestCase.original_title}
                      </div>
                    )}
                  </div>

                  {loadingOriginal ? (
                    <div className="text-sm text-blue-600 text-center py-4">
                      Loading original test case...
                    </div>
                  ) : (
                    <>
                      {/* Original Steps */}
                      {selectedTestCase?.original_steps && selectedTestCase.original_steps.length > 0 ? (
                        <div className="space-y-2">
                          <div className="text-sm font-medium text-purple-600">Test Steps</div>
                          <div className="space-y-2">
                            {selectedTestCase.original_steps.map((step, index) => (
                              <div key={index} className="flex items-start gap-3 bg-white p-3 rounded-lg border border-purple-100">
                                <div className="flex-shrink-0 w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center text-purple-700 text-sm font-medium">
                                  {index + 1}
                                </div>
                                <div className="text-sm">{step}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="text-sm text-purple-600 italic p-3 bg-white rounded-lg border border-purple-100">
                          No original test steps available
                        </div>
                      )}

                      {/* Original Expected Result */}
                      {selectedTestCase?.original_expected_result ? (
                        <div className="space-y-2 mt-4">
                          <div className="text-sm font-medium text-purple-600">Expected Result</div>
                          <div className="text-sm leading-relaxed bg-white p-4 rounded-lg border border-purple-100">
                            {selectedTestCase.original_expected_result}
                          </div>
                        </div>
                      ) : (
                        <div className="text-sm text-purple-600 italic p-3 bg-white rounded-lg border border-purple-100 mt-4">
                          No original expected result available
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Test Steps */}
            {selectedTestCase?.steps && selectedTestCase.steps.length > 0 && (
              <div className="space-y-2">
                <div className="text-sm font-medium text-amber-600">Test Steps</div>
                <div className="space-y-2">
                  {selectedTestCase.steps.map((step, index) => (
                    <div key={index} className="flex items-start gap-3 bg-amber-50 p-3 rounded-lg border border-amber-100">
                      <div className="flex-shrink-0 w-6 h-6 bg-amber-100 rounded-full flex items-center justify-center text-amber-700 text-sm font-medium">
                        {index + 1}
                      </div>
                      <div className="text-sm">{step}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Expected Result */}
            {selectedTestCase?.expected_result && (
              <div className="space-y-2">
                <div className="text-sm font-medium text-teal-600">Expected Result</div>
                <div className="text-sm leading-relaxed bg-teal-50 p-4 rounded-lg border border-teal-100">
                  {selectedTestCase.expected_result}
                </div>
              </div>
            )}

            {/* Tags and Analysis */}
            <div className="flex items-center gap-4 py-3 px-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex items-center gap-1.5 text-sm">
                <span className="font-medium text-red-600">Severity:</span>
                <span className="text-red-700">{selectedTestCase?.severity?.toUpperCase() || 'LOW'}</span>
              </div>
              <div className="w-px h-4 bg-gray-300" />
              <div className="flex items-center gap-1.5 text-sm">
                <span className="font-medium text-orange-600">Priority:</span>
                <span className="text-orange-700">{selectedTestCase?.priority?.toUpperCase() || 'LOW'}</span>
              </div>
              <div className="w-px h-4 bg-gray-300" />
              <div className="flex items-center gap-1.5 text-sm">
                <span className="font-medium text-violet-600">Generated by:</span>
                <div className="flex items-center gap-1 text-violet-700">
                  <Brain className="h-3.5 w-3.5" />
                  <span>AI</span>
                </div>
              </div>
              <div className="w-px h-4 bg-gray-300" />
              <div className="flex items-center gap-1.5 text-sm">
                <span className="font-medium text-indigo-600">Match:</span>
                <span className="text-indigo-700">{Math.round((selectedTestCase?.similarity_score || 0) * 100)}%</span>
              </div>
            </div>

            {/* Modified Date */}
            <div className="mt-6 pt-4 border-t border-gray-200">
              <div className="text-sm text-gray-600">
                Last Modified: {selectedTestCase?.modified_date ? new Date(selectedTestCase.modified_date).toLocaleString() : 'N/A'}
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}