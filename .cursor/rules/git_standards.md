# Git Standards

## Commit Messages
Follow the Conventional Commits specification (https://www.conventionalcommits.org/)

### Format
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semi colons, etc)
- `refactor`: Code changes that neither fix bugs nor add features
- `test`: Adding or modifying tests
- `chore`: Changes to build process or auxiliary tools
- `perf`: Performance improvements

### Guidelines
- Subject line limited to 72 characters
- Use imperative mood in subject line ("Add feature" not "Added feature")
- No period at the end of the subject line
- Separate subject from body with a blank line
- Wrap body text at 72 characters
- Use body to explain what and why, not how

## Branching Strategy
- `main`: Primary branch, always stable
- `develop`: Integration branch for features
- Feature branches: `feature/<feature-name>`
- Bug fix branches: `fix/<bug-description>`
- Release branches: `release/v<version>`

## Pull Requests
- Keep changes focused and atomic
- Include clear description of changes
- Reference related issues
- Update documentation as needed
- Ensure all tests pass
- Request review from at least one team member 