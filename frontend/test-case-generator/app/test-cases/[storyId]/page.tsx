"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, TestCase, TestCaseResponse } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp, Triangle } from "lucide-react";

export default function StoryTestCasesPage() {
  const params = useParams();
  const storyId = typeof params?.storyId === 'string' ? params.storyId : Array.isArray(params?.storyId) ? params.storyId[0] : '';
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [storyDescription, setStoryDescription] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [currentTime, setCurrentTime] = useState<string>("");

  useEffect(() => {
    if (storyId) {
      fetchTestCases();
    }
    // eslint-disable-next-line
  }, [storyId]);

  useEffect(() => {
    const updateTime = () => {
      setCurrentTime(new Date().toLocaleTimeString());
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const fetchTestCases = async () => {
    setLoading(true);
    setError(null);
    try {
      const response: TestCaseResponse = await api.getTestCases(storyId);
      setTestCases(response.testcases);
      setStoryDescription(response.storyDescription || null);
    } catch (err) {
      setError("Failed to fetch test cases. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleExpand = (idx: number) => {
    setExpanded(expanded === idx ? null : idx);
  };

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
      <div className="max-w-4xl mx-auto w-full">
        <Card className="shadow-lg border border-gray-200 rounded-xl overflow-hidden mb-8">
          <CardHeader className="bg-blue-50 border-b border-gray-200">
            <CardTitle className="text-2xl font-bold text-blue-800">
              Test Cases for {storyId}
            </CardTitle>
            {storyDescription && <div className="text-gray-600 mt-2">{storyDescription}</div>}
          </CardHeader>
          {/* AI-generated note */}
          <div className="flex items-center gap-2 bg-yellow-50 border-l-4 border-yellow-400 text-yellow-800 px-4 py-2 mb-4 rounded">
            <svg className="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M12 20a8 8 0 100-16 8 8 0 000 16z" /></svg>
            <span className="font-medium">These test cases are generated by AI.</span>
          </div>
          <CardContent className="bg-white">
            {loading ? (
              <div className="p-8 text-center text-blue-600 font-semibold">Loading...</div>
            ) : error ? (
              <div className="p-8 text-center text-red-600 font-semibold">{error}</div>
            ) : testCases.length === 0 ? (
              <div className="p-8 text-center text-gray-600">No test cases found for this story.</div>
            ) : (
              <ul className="space-y-4">
                {testCases.map((tc, idx) => (
                  <li key={tc.test_case_id} className="border rounded-lg p-4 bg-gray-50">
                    <div className="flex items-center justify-between cursor-pointer" onClick={() => handleExpand(idx)}>
                      <div>
                        <div className="font-semibold text-blue-800">{tc.title}</div>
                        <div className="text-gray-600 text-sm">Test Case ID: <span className="font-mono">{tc.test_case_id}</span></div>
                        <div className="text-gray-600 text-sm">Priority: {tc.priority}</div>
                      </div>
                      <Button variant="ghost" size="icon">
                        {expanded === idx ? <ChevronUp /> : <ChevronDown />}
                      </Button>
                    </div>
                    {expanded === idx && (
                      <div className="mt-4 space-y-2">
                        <div>
                          <span className="font-medium text-gray-700">Description:</span>
                          <span className="ml-2 text-gray-700">{tc.description}</span>
                        </div>
                        <div>
                          <span className="font-medium text-gray-700">Steps:</span>
                          <ol className="list-decimal ml-6 text-gray-700">
                            {tc.steps.map((step, i) => (
                              <li key={i}>{step}</li>
                            ))}
                          </ol>
                        </div>
                        <div>
                          <span className="font-medium text-gray-700">Expected Result:</span>
                          <span className="ml-2 text-gray-700">{tc.expected_result}</span>
                        </div>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
} 