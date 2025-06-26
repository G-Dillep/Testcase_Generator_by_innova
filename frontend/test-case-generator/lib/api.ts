const API_BASE_URL = "http://127.0.0.1:5000/api/stories";

export interface Story {
  id: string;
  description: string;
  document_content: string | null;
  created_on: string;
  test_case_count: number;
  embedding_timestamp: string | null;
  test_case_created_time: string | null;
  project_id: string;
  title?: string;
  summary?: string;
  doc_content_text?: string;
  impactedTestCases?: number;
}

export interface TestCase {
  test_case_id?: string;
  id?: string;
  title: string;
  description?: string;
  steps?: string[];
  expected_result?: string;
  expected_results?: string[];
  priority?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  original_version?: TestCase; // For comparison
}

export interface ImpactedTestCase extends TestCase {
  similarity_score: number;
  original_test_case?: TestCase;
}

export interface TestCaseResponse {
  storyID: string;
  storyDescription: string | null;
  project_id?: string;
  testcases: TestCase[];
}

export interface ImpactAnalysisResponse {
  story_id: string;
  impacted_test_cases: ImpactedTestCase[];
  total_impacted: number;
}

export const api = {
  // Fetch paginated stories
  getStories: async (page: number = 1, perPage: number = 10, from_date?: string, to_date?: string, project_id?: string, sort_order: 'desc' | 'asc' = 'desc') => {
    let url = `${API_BASE_URL}/?page=${page}&per_page=${perPage}&sort_order=${sort_order}`;
    if (from_date) url += `&from_date=${encodeURIComponent(from_date)}`;
    if (to_date) url += `&to_date=${encodeURIComponent(to_date)}`;
    if (project_id) url += `&project_id=${encodeURIComponent(project_id)}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error("Failed to fetch stories");
    return response.json();
  },

  // Search stories
  searchStories: async (query: string, limit: number = 3) => {
    const response = await fetch(`${API_BASE_URL}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit }),
    });
    if (!response.ok) throw new Error("Failed to search stories");
    return response.json();
  },

  // Fetch test cases for a story
  getTestCases: async (storyId: string) => {
    const response = await fetch(`${API_BASE_URL}/${storyId}/testcases`);
    if (!response.ok) throw new Error("Failed to fetch test cases");
    return response.json();
  },

  // Get unique project IDs
  getProjects: async () => {
    const response = await fetch(`${API_BASE_URL}/projects`);
    if (!response.ok) throw new Error("Failed to fetch projects");
    return response.json();
  },

  // New methods for impact analysis
  getStoryImpacts: async (storyId: string): Promise<ImpactAnalysisResponse> => {
    const response = await fetch(`${API_BASE_URL}/impacts/story/${storyId}`);
    if (!response.ok) throw new Error("Failed to fetch impact analysis");
    return response.json();
  },

  getImpactDetails: async (impactId: string) => {
    const response = await fetch(`${API_BASE_URL}/impacts/details/${impactId}`);
    if (!response.ok) throw new Error("Failed to fetch impact details");
    return response.json();
  },

  getImpactSummary: async (projectId: string) => {
    const response = await fetch(`${API_BASE_URL}/impacts/summary/${projectId}`);
    if (!response.ok) throw new Error("Failed to fetch impact summary");
    return response.json();
  },
}; 