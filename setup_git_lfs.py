#!/usr/bin/env python3
"""
Setup Git LFS for large archive files and configure repository for GitHub upload
"""

import os
import subprocess
import json
from pathlib import Path
import logging

class GitLFSSetup:
    """Setup Git LFS for handling large archive files"""
    
    def __init__(self, archives_dir: str = './archives'):
        self.archives_dir = Path(archives_dir)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def run_command(self, command: str, check: bool = True) -> tuple:
        """Run a shell command and return (success, output)"""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=check)
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {command}")
            self.logger.error(f"Error: {e.stderr}")
            return False, e.stderr
    
    def check_git_lfs_installed(self) -> bool:
        """Check if Git LFS is installed"""
        success, output = self.run_command("git lfs version", check=False)
        if success:
            self.logger.info(f"Git LFS is installed: {output}")
            return True
        else:
            self.logger.error("Git LFS is not installed. Please install it first:")
            self.logger.error("  macOS: brew install git-lfs")
            self.logger.error("  Ubuntu: sudo apt install git-lfs")
            self.logger.error("  Windows: Download from https://git-lfs.github.io/")
            return False
    
    def initialize_git_lfs(self) -> bool:
        """Initialize Git LFS in the repository"""
        self.logger.info("Initializing Git LFS...")
        
        success, output = self.run_command("git lfs install")
        if success:
            self.logger.info("Git LFS initialized successfully")
            return True
        else:
            self.logger.error("Failed to initialize Git LFS")
            return False
    
    def analyze_archive_sizes(self) -> dict:
        """Analyze archive sizes to determine which need LFS"""
        if not self.archives_dir.exists():
            self.logger.warning(f"Archives directory does not exist: {self.archives_dir}")
            return {}
        
        self.logger.info("Analyzing archive file sizes...")
        
        size_analysis = {
            'small_files': [],      # < 50 MB
            'medium_files': [],     # 50-100 MB  
            'large_files': [],      # > 100 MB (need LFS)
            'total_size': 0,
            'total_files': 0
        }
        
        # Scan all ZIP files
        for zip_file in self.archives_dir.rglob("*.zip"):
            file_size = zip_file.stat().st_size
            size_mb = file_size / (1024 * 1024)
            
            size_analysis['total_size'] += file_size
            size_analysis['total_files'] += 1
            
            file_info = {
                'path': str(zip_file.relative_to(self.archives_dir)),
                'size_bytes': file_size,
                'size_mb': round(size_mb, 2)
            }
            
            if size_mb < 50:
                size_analysis['small_files'].append(file_info)
            elif size_mb < 100:
                size_analysis['medium_files'].append(file_info)
            else:
                size_analysis['large_files'].append(file_info)
        
        # Log analysis results
        total_size_gb = size_analysis['total_size'] / (1024**3)
        self.logger.info(f"Archive size analysis:")
        self.logger.info(f"  Total files: {size_analysis['total_files']}")
        self.logger.info(f"  Total size: {total_size_gb:.2f} GB")
        self.logger.info(f"  Small files (< 50 MB): {len(size_analysis['small_files'])}")
        self.logger.info(f"  Medium files (50-100 MB): {len(size_analysis['medium_files'])}")
        self.logger.info(f"  Large files (> 100 MB): {len(size_analysis['large_files'])}")
        
        if size_analysis['large_files']:
            self.logger.info("Large files that will use Git LFS:")
            for file_info in size_analysis['large_files']:
                self.logger.info(f"    {file_info['path']}: {file_info['size_mb']} MB")
        
        return size_analysis
    
    def setup_gitattributes(self, size_analysis: dict) -> bool:
        """Setup .gitattributes file for Git LFS"""
        gitattributes_path = Path('.gitattributes')
        
        # Base LFS rules
        lfs_rules = [
            "# Git LFS configuration for Brazilian Chamber PDF archives",
            "",
            "# Track ZIP files over 100 MB with LFS",
            "archives/**/*.zip filter=lfs diff=lfs merge=lfs -text",
            "",
            "# Track large log files",
            "*.log filter=lfs diff=lfs merge=lfs -text",
            "",
            "# Track large JSON manifests over 10 MB",
            "master-manifest.json filter=lfs diff=lfs merge=lfs -text",
            "",
            "# Standard Git LFS file types",
            "*.zip filter=lfs diff=lfs merge=lfs -text",
            "*.7z filter=lfs diff=lfs merge=lfs -text",
            "*.tar.gz filter=lfs diff=lfs merge=lfs -text",
            "*.rar filter=lfs diff=lfs merge=lfs -text"
        ]
        
        # Write .gitattributes
        try:
            with open(gitattributes_path, 'w') as f:
                f.write('\n'.join(lfs_rules))
            
            self.logger.info(f"Created .gitattributes with LFS rules")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create .gitattributes: {e}")
            return False
    
    def update_gitignore(self) -> bool:
        """Update .gitignore to exclude temporary files but include archives"""
        gitignore_path = Path('.gitignore')
        
        # Additional ignore rules for our compression process
        additional_rules = [
            "",
            "# Compression process files",
            "compression.log",
            "test_output.log",
            "",
            "# Temporary extraction folders",
            "extracted/",
            "temp/",
            "",
            "# Keep archives directory but ignore if too large",
            "# archives/",
            "",
            "# Python cache and virtual environments",
            "__pycache__/",
            "*.pyc",
            "venv/",
            ".env"
        ]
        
        try:
            # Read existing .gitignore if it exists
            existing_content = ""
            if gitignore_path.exists():
                with open(gitignore_path, 'r') as f:
                    existing_content = f.read()
            
            # Check if our rules are already present
            if "# Compression process files" not in existing_content:
                with open(gitignore_path, 'a') as f:
                    f.write('\n'.join(additional_rules))
                self.logger.info("Updated .gitignore with compression rules")
            else:
                self.logger.info(".gitignore already contains compression rules")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update .gitignore: {e}")
            return False
    
    def create_upload_script(self) -> bool:
        """Create a script to help with uploading archives to GitHub"""
        upload_script = '''#!/bin/bash
# Upload Brazilian Chamber PDF archives to GitHub
# This script helps manage the upload process for large files

echo "========================================="
echo "Brazilian Chamber PDF Archive Uploader"
echo "========================================="
echo

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "Error: Not in a git repository!"
    exit 1
fi

# Check if Git LFS is installed
if ! command -v git-lfs &> /dev/null; then
    echo "Error: Git LFS is not installed!"
    echo "Please install Git LFS first:"
    echo "  macOS: brew install git-lfs"
    echo "  Ubuntu: sudo apt install git-lfs"
    exit 1
fi

# Initialize Git LFS if not already done
echo "Initializing Git LFS..."
git lfs install

# Add all archive files
echo "Adding archive files to git..."
git add archives/
git add *.py
git add *.md
git add .gitattributes
git add .gitignore

# Check repository size
echo "Checking repository size..."
git count-objects -vH

# Show LFS files
echo "Git LFS tracked files:"
git lfs ls-files

# Commit changes
echo "Committing changes..."
read -p "Enter commit message (or press Enter for default): " commit_msg
if [ -z "$commit_msg" ]; then
    commit_msg="Add compressed PDF archives for Brazilian Chamber documents"
fi

git commit -m "$commit_msg"

# Push to GitHub
echo "Pushing to GitHub..."
echo "Note: This may take a while for large files..."
git push origin main

echo "Upload completed!"
echo "Check your GitHub repository for the uploaded archives."
'''
        
        upload_script_path = Path('upload_to_github.sh')
        try:
            with open(upload_script_path, 'w') as f:
                f.write(upload_script)
            
            # Make script executable
            os.chmod(upload_script_path, 0o755)
            
            self.logger.info(f"Created upload script: {upload_script_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create upload script: {e}")
            return False
    
    def setup_all(self) -> bool:
        """Setup complete Git LFS configuration"""
        self.logger.info("Setting up Git LFS for archive uploads...")
        
        # Check if Git LFS is installed
        if not self.check_git_lfs_installed():
            return False
        
        # Initialize Git LFS
        if not self.initialize_git_lfs():
            return False
        
        # Analyze archive sizes (if archives exist)
        size_analysis = self.analyze_archive_sizes()
        
        # Setup .gitattributes
        if not self.setup_gitattributes(size_analysis):
            return False
        
        # Update .gitignore
        if not self.update_gitignore():
            return False
        
        # Create upload script
        if not self.create_upload_script():
            return False
        
        self.logger.info("Git LFS setup completed successfully!")
        self.logger.info("Next steps:")
        self.logger.info("1. Run 'python compress_downloads.py' to create archives")
        self.logger.info("2. Run './upload_to_github.sh' to upload to GitHub")
        
        return True


def main():
    """Main entry point"""
    import sys
    
    archives_dir = './archives'
    
    if len(sys.argv) > 1:
        archives_dir = sys.argv[1]
    
    print(f"Setting up Git LFS for archives in: {archives_dir}")
    print()
    
    lfs_setup = GitLFSSetup(archives_dir)
    success = lfs_setup.setup_all()
    
    if success:
        print("\nGit LFS setup completed successfully!")
    else:
        print("\nGit LFS setup failed. Check the logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
