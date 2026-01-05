# Contributing to LanComm

Thank you for your interest in contributing to LanComm! This document provides guidelines and information for contributors.

## 🎯 Ways to Contribute

- **Bug Reports**: Found a bug? [Open an issue](https://github.com/zeostjh/LanComm/issues/new)
- **Feature Requests**: Have an idea? Start a [discussion](https://github.com/zeostjh/LanComm/discussions)
- **Code Contributions**: Submit pull requests for bug fixes or new features
- **Documentation**: Improve guides, fix typos, add examples
- **Testing**: Test on different hardware platforms and report results
- **Community**: Help others in discussions and issues

## 🚀 Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- PyQt6 (GUI testing)
- Audio hardware or virtual audio cables

### Clone and Install

```bash
# Fork the repository on GitHub first
git clone https://github.com/zeostjh/LanComm.git
cd LanComm

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\\Scripts\\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install black pylint pytest
```

## 📝 Code Style

We follow PEP 8 with some modifications:

- **Line Length**: 120 characters (increased from 80 for readability)
- **Imports**: Group by standard library, third-party, local imports
- **Docstrings**: Use Google-style docstrings
- **Type Hints**: Encouraged but not required

### Format Code

```bash
# Auto-format with black
black *.py

# Check style
pylint server.py beltpack.py
```

## 🔧 Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-recording` - New features
- `bugfix/audio-dropout` - Bug fixes
- `docs/update-wiring` - Documentation updates
- `refactor/cleanup-mixer` - Code refactoring

### Commit Messages

Follow conventional commits format:

```
feat: add recording functionality
fix: resolve audio dropout on channel switch
docs: update wiring diagram for Orange Pi 5
refactor: simplify mixer logic
test: add unit tests for audio pipeline
```

### Testing

Before submitting:

1. Test on real hardware if possible
2. Run existing tests: `pytest tests/`
3. Test both server and beltpack components
4. Verify cross-platform compatibility (Windows/Linux/Mac)

## 📥 Pull Request Process

1. **Create Issue First**: For major changes, open an issue to discuss
2. **Fork Repository**: Work in your own fork
3. **Create Branch**: Use descriptive branch name
4. **Make Changes**: Follow code style guidelines
5. **Test Thoroughly**: Verify your changes work
6. **Update Documentation**: Add/update docs if needed
7. **Submit PR**: Include clear description of changes

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Code refactoring

## Testing
Describe how you tested your changes

## Hardware Tested
- [ ] Windows server
- [ ] Linux server
- [ ] Orange Pi 5 Pro beltpack
- [ ] Raspberry Pi 4 beltpack
- [ ] Other (specify)

## Checklist
- [ ] Code follows project style
- [ ] Documentation updated
- [ ] Tested on real hardware
- [ ] No breaking changes (or documented)
```

## 🐛 Bug Reports

Good bug reports include:

1. **Clear Title**: Describe the issue concisely
2. **Environment**: 
   - OS and version
   - Python version
   - Hardware (if applicable)
3. **Steps to Reproduce**: Detailed steps
4. **Expected Behavior**: What should happen
5. **Actual Behavior**: What actually happens
6. **Logs**: Include relevant error messages
7. **Screenshots**: If GUI issue

## 💡 Feature Requests

When suggesting features:

1. **Use Case**: Explain why this feature is needed
2. **Current Workaround**: How do you solve this now?
3. **Proposed Solution**: How should it work?
4. **Alternatives**: Any other approaches considered?
5. **Impact**: Who would benefit from this?

## 📚 Documentation

Documentation improvements are always welcome:

- Fix typos and grammar
- Add missing information
- Improve clarity
- Add examples
- Update diagrams

Documentation files are in:
- `README.md` - Main project documentation
- `docs/` - Detailed guides
- Code comments and docstrings

## 🎨 Design Principles

When contributing, keep these principles in mind:

1. **Simplicity**: Favor simple solutions over complex ones
2. **Performance**: Minimize latency in audio pipeline
3. **Reliability**: Handle errors gracefully, auto-reconnect
4. **Usability**: GUI should be intuitive, hardware controls responsive
5. **Compatibility**: Support multiple platforms and hardware

## 🏗️ Architecture Guidelines

### Server (`server.py`)
- Keep GUI thread separate from network I/O
- Use asyncio for network operations
- Thread-safe access to shared state (use locks)
- Minimize audio processing latency

### Beltpack (`beltpack.py`)
- Hardware detection and graceful fallback
- Efficient GPIO polling (avoid busy-wait)
- Queue-based audio I/O to prevent blocking
- Auto-reconnection on network failures

## 📖 Helpful Resources

- [PyQt6 Documentation](https://doc.qt.io/qtforpython/)
- [Python asyncio Guide](https://docs.python.org/3/library/asyncio.html)
- [PyAudio Documentation](http://people.csail.mit.edu/hubert/pyaudio/docs/)
- [GPIO in Linux](https://github.com/brgl/libgpiod)

## 🤝 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the issue, not the person
- Help newcomers learn
- Assume good intentions

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## ❓ Questions?

- Open a [Discussion](https://github.com/zeostjh/LanComm/discussions)
- Join community chat (if available)
- Contact via GitHub

---

**Thank you for contributing to LanComm! 🎉**
