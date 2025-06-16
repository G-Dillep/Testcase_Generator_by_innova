import pandas as pd
from io import BytesIO
from datetime import datetime

def generate_excel(test_cases_data):
    """
    Generate Excel file from test case data
    """
    try:
        # Create a BytesIO object to store the Excel file
        output = BytesIO()
        
        # Create a DataFrame from the test cases data
        rows = []
        
        # Extract story information
        story_id = test_cases_data.get('storyID', '')
        story_description = test_cases_data.get('storyDescription', '')
        
        # Extract test cases
        test_cases = test_cases_data.get('testcases', [])
        if isinstance(test_cases, str):
            import json
            try:
                test_cases = json.loads(test_cases)
            except json.JSONDecodeError:
                test_cases = []
        
        # Process each test case
        for tc in test_cases:
            if isinstance(tc, dict):
                # Extract steps
                steps = tc.get('steps', [])
                if isinstance(steps, list):
                    steps_text = '\n'.join([f"{i+1}. {step}" for i, step in enumerate(steps)])
                else:
                    steps_text = str(steps)
                
                # Create row with all fields
                row = {
                    'Story ID': story_id,
                    'Story Description': story_description,
                    'Test Case ID': tc.get('id', ''),
                    'Title': tc.get('title', ''),
                    'Steps': steps_text,
                    'Expected Result': tc.get('expected_result', ''),
                    'Priority': tc.get('priority', '')
                }
                rows.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Write to Excel
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Test Cases', index=False)
            
            # Get workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Test Cases']
            
            # Add header format
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'bg_color': '#D9E1F2',
                'border': 1
            })
            
            # Add cell format
            cell_format = workbook.add_format({
                'text_wrap': True,
                'valign': 'top',
                'border': 1
            })
            
            # Apply formats
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 30, cell_format)
            
            # Auto-adjust column widths
            for i, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                )
                # Limit width to 50 characters
                max_length = min(max_length, 50)
                worksheet.set_column(i, i, max_length + 2)
        
        # Reset buffer position
        output.seek(0)
        return output
        
    except Exception as e:
        print(f"Error generating Excel: {str(e)}")
        raise 