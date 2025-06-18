import pandas as pd
from io import BytesIO
from datetime import datetime

def generate_excel(test_cases_data):
    """
    Generate Excel file from test case data with improved formatting
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
                
                # Extract expected results
                expected_results = tc.get('expected_result', [])
                if isinstance(expected_results, list):
                    expected_text = '\n'.join([f"• {result}" for result in expected_results])
                else:
                    expected_text = tc.get('expected_result', '')
                
                # Create row with all fields
                row = {
                    'Story ID': story_id,
                    'Story Description': story_description,
                    'Test Case ID': tc.get('id', ''),
                    'Title': tc.get('title', ''),
                    'Steps': steps_text,
                    'Expected Results': expected_text,
                    'Priority': tc.get('priority', ''),
                    'Status': tc.get('status', 'New')
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
                'align': 'center',
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1
            })
            
            # Add cell format
            cell_format = workbook.add_format({
                'text_wrap': True,
                'valign': 'top',
                'border': 1
            })
            
            # Add steps and expected results format
            steps_format = workbook.add_format({
                'text_wrap': True,
                'valign': 'top',
                'border': 1,
                'align': 'left'
            })
            
            # Add expected results format with bullet points
            expected_format = workbook.add_format({
                'text_wrap': True,
                'valign': 'top',
                'border': 1,
                'align': 'left',
                'indent': 1
            })
            
            # Apply formats
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                
                # Set column widths
                if value in ['Story ID', 'Test Case ID', 'Priority', 'Status']:
                    worksheet.set_column(col_num, col_num, 15, cell_format)
                elif value in ['Title']:
                    worksheet.set_column(col_num, col_num, 30, cell_format)
                elif value in ['Steps']:
                    worksheet.set_column(col_num, col_num, 50, steps_format)
                elif value in ['Expected Results']:
                    worksheet.set_column(col_num, col_num, 50, expected_format)
                else:
                    worksheet.set_column(col_num, col_num, 40, cell_format)
            
            # Merge cells for story information
            if len(df) > 0:
                worksheet.merge_range(1, 0, len(df), 0, story_id, cell_format)  # Story ID
                worksheet.merge_range(1, 1, len(df), 1, story_description, cell_format)  # Story Description
            
            # Add status dropdown validation
            status_col = df.columns.get_loc('Status')
            worksheet.data_validation(1, status_col, len(df), status_col, {
                'validate': 'list',
                'source': ['New', 'In Progress', 'Completed'],
                'input_message': 'Select status',
                'error_message': 'Please select a valid status',
                'show_dropdown': True
            })
            
            # Add alternating row colors
            for row in range(1, len(df) + 1):
                if row % 2 == 0:
                    worksheet.set_row(row, None, workbook.add_format({
                        'bg_color': '#F2F2F2',
                        'text_wrap': True,
                        'valign': 'top',
                        'border': 1
                    }))
        
        # Reset buffer position
        output.seek(0)
        return output
        
    except Exception as e:
        print(f"Error generating Excel: {str(e)}")
        raise