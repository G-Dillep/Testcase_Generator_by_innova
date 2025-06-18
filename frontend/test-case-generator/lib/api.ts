const API_BASE_URL = "http://127.0.0.1:5000/api/stories";

export interface Story {
  id: string;
  description: string;
  document_content: string | null;
  created_on: string;
  test_case_count: number;
  embedding_timestamp: string | null;
  test_case_created_time: string | null;
  title?: string;
  summary?: string;
  doc_content_text?: string;
  // Add other fields as needed
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
}

export interface TestCaseResponse {
  storyID: string;
  storyDescription: string | null;
  testcases: TestCase[];
}

export const api = {
  // Fetch paginated stories
  getStories: async (page: number = 1, perPage: number = 10, from_date?: string, to_date?: string) => {
    let url = `${API_BASE_URL}/?page=${page}&per_page=${perPage}`;
    if (from_date) url += `&from_date=${encodeURIComponent(from_date)}`;
    if (to_date) url += `&to_date=${encodeURIComponent(to_date)}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error("Failed to fetch stories");
    return response.json();
  },

  // Search stories
  searchStories: async (query: string, limit: number = 5) => {
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
}; 