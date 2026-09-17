"""Single exception type carrying a category and exit code (SPEC.md §8)."""


class PromptlabError(Exception):
    def __init__(self, category: str, message: str, exit_code: int):
        super().__init__(message)
        self.category = category
        self.message = message
        self.exit_code = exit_code

    def __str__(self):
        return f"promptlab: {self.category}: {self.message}"
