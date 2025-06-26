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

// Mock function to generate QA support response when API key is not available
function generateMockQASupport(question: string) {
  const questionSnippet = question.length > 30 ? question.substring(0, 30) + "..." : question

  return `# QA Support Response

## Question: ${questionSnippet}

## Answer:

I'm here to help with software testing and QA-related questions! Here are some common topics I can assist with:

### 🧪 **Testing Methodologies**
- Unit Testing, Integration Testing, System Testing
- Manual vs Automated Testing approaches
- Test-Driven Development (TDD) and Behavior-Driven Development (BDD)

### 🛠️ **Testing Tools & Frameworks**
- Popular testing frameworks (JUnit, TestNG, PyTest, etc.)
- Test automation tools (Selenium, Cypress, Playwright)
- Performance testing tools (JMeter, LoadRunner)

### 📋 **QA Processes**
- Test planning and strategy
- Bug reporting and tracking
- Test case design and management
- Quality metrics and KPIs

### 🔍 **Best Practices**
- Test case writing guidelines
- Test data management
- Environment setup and management
- Continuous Integration/Continuous Testing

**Note**: For test case generation based on your specific user stories, please use the RAG mode instead. I'm here to provide guidance and answer questions about QA processes and methodologies.

What specific aspect of software testing would you like to learn more about?`
}

export async function POST(request: Request) {
  try {
    const { message, context, model } = await request.json()

    if (model === 'rag') {
      // Call Flask backend RAG endpoint for test case generation
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

    // Gemini mode - only for QA support questions, not test case generation
    const apiKey = process.env.GOOGLE_GENERATIVE_AI_API_KEY

    let responseText = ""

    if (!apiKey) {
      console.log("API key not found, using mock QA support response")
      // Use mock implementation when API key is not available
      responseText = generateMockQASupport(message)
    } else {
      // Use the real Gemini API for QA support only
      const { text } = await generateText({
        model: google("gemini-1.5-flash"),
        providerOptions: {
          google: {
            apiKey: apiKey,
          },
        },
        system: `You are an expert QA engineer and software testing consultant. Your role is to provide guidance, best practices, and answers to questions about software testing, quality assurance processes, and testing methodologies.

You should NOT generate test cases. Instead, focus on:
- Explaining testing concepts and methodologies
- Providing best practices for QA processes
- Answering questions about testing tools and frameworks
- Giving advice on test planning and strategy
- Explaining different types of testing (unit, integration, system, etc.)
- Discussing test automation approaches
- Providing guidance on bug reporting and tracking
- Explaining quality metrics and KPIs

Keep your responses professional, informative, and focused on QA/software testing topics. If someone asks for test case generation, politely redirect them to use the RAG mode instead.`,
        prompt: `User Question: ${message}

Please provide a helpful answer about software testing, QA processes, or best practices. Do NOT generate test cases - focus on providing guidance and information.`,
        maxTokens: 2000,
      })

      responseText = text
    }

    return Response.json({ response: responseText })
  } catch (error) {
    console.error("Error in QA support:", error)

    // Provide a more helpful error message and fallback to mock data
    const mockResponse = generateMockQASupport("Error occurred, using fallback QA support")

    return Response.json({
      response: mockResponse,
      error: "API key missing or error occurred. Using mock QA support for demonstration.",
    })
  }
}
