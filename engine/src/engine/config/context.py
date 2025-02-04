from enum import Enum
from typing import Union, Dict, Any

class Role(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Context(str):
    """
    A string subclass that maintains context for AI chat messages.
    Behaves exactly like a string but with additional role information.
    """
    
    def __new__(cls, content: str, role: Union[Role, str] = Role.USER):
        # Create a new string instance
        instance = super().__new__(cls, content)
        
        # Convert string type to enum if necessary
        if isinstance(role, str):
            try:
                role = Role(role.lower())
            except ValueError:
                raise ValueError(f"Invalid role: {role}. Must be one of: {[r.value for r in Role]}")
        
        # Set the role
        instance._role = role
        return instance
    
    @property
    def role(self) -> Role:
        """Get the role."""
        return self._role
    
    def to_message(self) -> Dict[str, str]:
        """
        Convert the Context to a message format compatible with LiteLLM.
        Returns a dict with 'role' and 'content' keys.
        """
        return {
            "role": self.role.value,
            "content": str(self)
        }
    
    @classmethod
    def from_message(cls, message: Dict[str, str]) -> 'Context':
        """
        Create a Context instance from a LiteLLM-compatible message dict.
        
        Args:
            message: Dict containing 'role' and 'content' keys
        
        Returns:
            Context instance
        """
        if not isinstance(message, dict):
            raise ValueError("Message must be a dictionary")
        
        required_keys = {'role', 'content'}
        if not all(key in message for key in required_keys):
            raise ValueError(f"Message must contain keys: {required_keys}")
            
        return cls(message['content'], message['role'])
    
    def __add__(self, other):
        """
        Implement string concatenation while preserving role.
        Returns a new Context with the same role as the left operand.
        """
        if isinstance(other, (str, Context)):
            return Context(super().__add__(other), self.role)
        return NotImplemented
    
    def __repr__(self):
        return f'Context("{super().__str__()}", {self.role.value})'
    
    def __eq__(self, other):
        """
        Equal if both content and role match.
        """
        if isinstance(other, Context):
            return super().__eq__(other) and self.role == other.role
        return super().__eq__(other)

# Example usage and tests
# if __name__ == "__main__":
#     # Basic creation and role checking
#     user_ctx = Context("Hello!", Role.USER)
#     assert isinstance(user_ctx, str)
#     assert user_ctx.role == Role.USER
#     assert user_ctx == "Hello!"
    
#     # Test message conversion
#     message = user_ctx.to_message()
#     assert message == {"role": "user", "content": "Hello!"}
    
#     # Test creating from message
#     new_ctx = Context.from_message({"role": "assistant", "content": "Hi there!"})
#     assert new_ctx.role == Role.ASSISTANT
#     assert str(new_ctx) == "Hi there!"
    
#     # String operations
#     assistant_ctx = Context("How can I help?", "assistant")
#     combined = user_ctx + " " + assistant_ctx
#     assert isinstance(combined, Context)
#     assert combined.role == Role.USER  # Takes role from left operand
#     assert combined == "Hello! How can I help?"
    
#     # String methods work as expected
#     upper_ctx = user_ctx.upper()
#     assert isinstance(upper_ctx, str)  # Note: Built-in string methods return regular strings
#     assert upper_ctx == "HELLO!"
    
#     # Error handling
#     try:
#         invalid_ctx = Context("Test", "invalid_role")
#         assert False, "Should have raised ValueError"
#     except ValueError:
#         pass
        
#     # Test invalid message format
#     try:
#         Context.from_message({"invalid": "format"})
#         assert False, "Should have raised ValueError"
#     except ValueError:
#         pass
    
#     print("All tests passed!")