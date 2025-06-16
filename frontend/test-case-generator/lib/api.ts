const API_BASE_URL = "http://127.0.0.1:5000/api/stories";

export interface Story {
  id: string;
  description: string;
  num_test_cases: number;
  created_on?: string; // ISO string from backend
  // Add other fields as needed
}

export interface TestCase {
  test_case_id: string;
  title: string;
  description: string;
  steps: string[];
  expected_result: string;
  priority: string;
}

export interface TestCaseResponse {
  storyID: string;
  storyDescription: string | null;
  testcases: TestCase[];
}

export const api = {
  // Fetch paginated stories
  getStories: async (page: number = 1, perPage: number = 10) => {
    const response = await fetch(`${API_BASE_URL}/?page=${page}&per_page=${perPage}`);
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