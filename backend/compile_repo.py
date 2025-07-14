import os
import datetime

def compile_repository_code(repo_path, output_file):
    """
    Recursively compile all code files from a repository into a single text file
    with file structure references.
    
    Args:
        repo_path (str): Path to the repository root directory
        output_file (str): Path where the output file will be created
    """
    # List of file extensions to include
    code_extensions = {
        '.js', '.jsx', '.ts', '.tsx',  # JavaScript/TypeScript
        '.css', '.scss', '.sass',      # Stylesheets
        '.html', '.htm',               # HTML
        '.json',                       # JSON files
        '.md',                         # Markdown
        '.yml', '.yaml',                 # YAML
        '.py',
    }
    
    # Files/directories to ignore
    ignore_patterns = {
        'node_modules',
        '.git',
        'build',
        'dist',
        '.DS_Store',
        '__pycache__',
        'coverage',
        'venv'
    }

    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Write header with timestamp
        outfile.write(f"Repository Code Compilation\n")
        outfile.write(f"Generated on: {datetime.datetime.now()}\n")
        outfile.write(f"Repository Path: {os.path.abspath(repo_path)}\n")
        outfile.write("="* 80 + "\n\n")

        for root, dirs, files in os.walk(repo_path):
            # Remove ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_patterns]
            
            # Process each file
            for file in files:
                if any(file.endswith(ext) for ext in code_extensions) and not any(ignore in file for ignore in ignore_patterns):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, repo_path)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # Write file header
                            outfile.write(f"File: {rel_path}\n")
                            outfile.write("-" * 80 + "\n")
                            
                            # Write file content
                            outfile.write(content)
                            outfile.write("\n\n" + "=" * 80 + "\n\n")
                    except Exception as e:
                        outfile.write(f"Error reading file {rel_path}: {str(e)}\n\n")

if __name__ == "__main__":
    # Get the current directory as default repo path
    default_repo_path = os.getcwd()
    
    # Get user input for paths
    repo_path = input(f"Enter repository path (press Enter for current directory - {default_repo_path}): ").strip()
    if not repo_path:
        repo_path = default_repo_path
    
    output_file = input("Enter output file path (default: repo_code_compilation.txt): ").strip()
    if not output_file:
        output_file = "repo_code_compilation.txt"
    
    # Run the compilation
    try:
        compile_repository_code(repo_path, output_file)
        print(f"\nCode compilation completed successfully!")
        print(f"Output file: {os.path.abspath(output_file)}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")