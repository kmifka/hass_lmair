# Light Manager Air Integration Guidelines

## Code Style Guidelines

### General Principles
- Maintain clean, readable, and consistent code
- Follow the Home Assistant code style guidelines
- Keep methods small and focused on a single task
- Use type hints where appropriate
- Write unit tests for new functionality

### Comments
- Write comments in English only
- Add comments only when necessary to explain complex logic
- Don't comment obvious code
- Use docstrings for classes and public methods

### Naming Conventions
- Use descriptive names for classes, methods, and variables
- Follow Python naming conventions:
  - snake_case for methods and variables
  - CamelCase for classes
  - UPPER_CASE for constants

## Release Process

### Tag and Release Format
- Tags should be created without "v" prefix: `1.2.2` (not `v1.2.2`)
- The release title should simply be the version number: `1.2.2`

### Creating a Release with GitHub CLI
```bash
# Create tag
git tag -a 1.2.2 -m "Release 1.2.2 - Brief description"
git push origin 1.2.2

# Create release
gh release create 1.2.2 --title "1.2.2" --notes "# Light Manager Air Integration 1.2.2

In version 1.2.2 of the Light Manager Air Integration for Home Assistant, the following changes have been made:

## Bug fixes
- Description of changes

Thank you for your feedback and support. Enjoy the new version!"
```

