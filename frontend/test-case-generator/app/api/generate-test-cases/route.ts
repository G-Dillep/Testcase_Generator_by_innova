import { google } from "@ai-sdk/google"
import { generateText } from "ai"

// Mock function to generate test cases when API key is not available
function generateMockTestCases(feature: string) {
  const featureName = feature.length > 30 ? feature.substring(0, 30) + "..." : feature

  return `# Test Cases for: ${featureName}

## Test Case ID: TC-001
**Test Case Title**: Verify Basic Functionality
**Objective**: Ensure the core functionality works as expected
**Preconditions**: User is logged in with valid credentials
**Test Steps**:
1. Navigate to the feature page
2. Enter valid input data
3. Submit the form
4. Verify the results
**Expected Results**: Feature performs the primary function correctly
**Priority**: High
**Test Type**: Functional

## Test Case ID: TC-002
**Test Case Title**: Validate Input Validation
**Objective**: Ensure the system properly validates user inputs
**Preconditions**: User has access to the feature
**Test Steps**:
1. Navigate to the feature page
2. Enter invalid data (e.g., special characters, extremely long text)
3. Submit the form
4. Observe system response
**Expected Results**: System should display appropriate error messages and prevent submission
**Priority**: Medium
**Test Type**: Validation

## Test Case ID: TC-003
**Test Case Title**: Test Error Handling
**Objective**: Verify the system handles errors gracefully
**Preconditions**: System is in a state where errors can occur
**Test Steps**:
1. Create conditions that would trigger an error
2. Execute the feature under these conditions
3. Observe how the system responds
**Expected Results**: System should display user-friendly error messages and recover gracefully
**Priority**: High
**Test Type**: Error Handling

## Test Case ID: TC-004
**Test Case Title**: Performance Under Load
**Objective**: Ensure the feature performs well under heavy usage
**Preconditions**: Test environment capable of simulating load
**Test Steps**:
1. Set up load testing tools
2. Simulate multiple concurrent users
3. Monitor system performance
**Expected Results**: System maintains acceptable response times and doesn't crash
**Priority**: Medium
**Test Type**: Performance

## Test Case ID: TC-005
**Test Case Title**: Mobile Responsiveness
**Objective**: Verify the feature works correctly on mobile devices
**Preconditions**: Access to mobile devices or emulators
**Test Steps**:
1. Access the feature on various mobile devices/screen sizes
2. Test all functionality
3. Check UI layout and usability
**Expected Results**: Feature is fully functional and visually correct on all tested devices
**Priority**: Medium
**Test Type**: UI/Compatibility

Note: These are mock test cases generated for demonstration purposes. In a production environment, the AI would generate more specific test cases tailored to your exact feature requirements.`
}

export async function POST(request: Request) {
  try {
    const { message, context, model } = await request.json()

    if (model === 'rag') {
      // Call Flask backend RAG endpoint
      const flaskRes = await fetch('http://127.0.0.1:5000/api/stories/rag-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: message })
      });
      const ragData = await flaskRes.json();
      if (!flaskRes.ok) {
        return Response.json({ error: ragData.error || 'RAG backend error' }, { status: 500 });
      }
      return Response.json({ testCases: ragData.testCases });
    }

    // Check if we have the Google API key
    const apiKey = process.env.GOOGLE_GENERATIVE_AI_API_KEY

    let responseText = ""

    if (!apiKey) {
      console.log("API key not found, using mock test cases")
      // Use mock implementation when API key is not available
      responseText = generateMockTestCases(message)
    } else {
      // Use the real Gemini API when key is available
      const { text } = await generateText({
        model: google("gemini-1.5-flash"),
        providerOptions: {
          google: {
            apiKey: apiKey,
          },
        },
        system: `You are an expert QA engineer and test case generator. Your role is to create comprehensive, detailed test cases for software features and user stories.

When generating test cases, follow this structure:
1. **Test Case ID**: Unique identifier
2. **Test Case Title**: Clear, descriptive title
3. **Objective**: What the test aims to verify
4. **Preconditions**: Setup requirements
5. **Test Steps**: Detailed step-by-step instructions
6. **Expected Results**: What should happen
7. **Priority**: High/Medium/Low
8. **Test Type**: Functional/UI/Integration/etc.

Generate multiple test cases covering:
- Happy path scenarios
- Edge cases
- Error handling
- Boundary conditions
- Negative test cases
- UI/UX validation

Format your response clearly with proper numbering and sections. Be thorough and professional.`,
        prompt: `${context}: ${message}

Please generate comprehensive test cases for this feature/story. Include both positive and negative test scenarios.`,
        maxTokens: 2000,
      })

      responseText = text
    }

    return Response.json({ response: responseText })
  } catch (error) {
    console.error("Error generating test cases:", error)

    // Provide a more helpful error message and fallback to mock data
    const mockResponse = generateMockTestCases("Error occurred, using fallback test cases")

    return Response.json({
      response: mockResponse,
      error: "API key missing or error occurred. Using mock test cases for demonstration.",
    })
  }
}
