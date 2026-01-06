"""Test script designed to require multiple iterations to fix.

This script has intentional bugs that will cause tests to fail:
1. Division by zero error - divide_numbers crashes when b=0
2. Logic error - find_maximum finds minimum instead of maximum
3. Missing type checking - process_data crashes with non-numeric inputs
4. Edge case - calculate_average returns 0 for empty list (should return None or raise)

The agent should need 2-3 iterations to fix all issues.
"""


def calculate_average(numbers):
    """Calculate the average of a list of numbers.
    
    Returns the mean of the numbers, or 0 if the list is empty.
    """
    if not numbers:
        return 0  # BUG: Should return None or raise ValueError
    total = sum(numbers)
    count = len(numbers)
    return total / count


def divide_numbers(a, b):
    """Divide two numbers.
    
    Args:
        a: Numerator
        b: Denominator
        
    Returns:
        a / b
        
    BUG: Will crash with ZeroDivisionError if b is 0
    """
    return a / b  # BUG: No check for b == 0


def process_data(data):
    """Process a list of data items by doubling each value.
    
    Args:
        data: List of numbers to process
        
    Returns:
        List with each value doubled
        
    BUG: Will crash if data contains non-numeric types
    """
    results = []
    for item in data:
        processed = item * 2  # BUG: Crashes if item is not a number
        results.append(processed)
    return results


def find_maximum(values):
    """Find the maximum value in a list.
    
    Args:
        values: List of numbers
        
    Returns:
        Maximum value, or None if list is empty
        
    BUG: Logic is reversed - finds minimum instead of maximum!
    """
    if not values:
        return None
    max_val = values[0]
    for val in values:
        if val < max_val:  # BUG: Should be val > max_val
            max_val = val
    return max_val


def validate_email(email):
    """Validate an email address format.
    
    Args:
        email: String to validate
        
    Returns:
        True if valid email format, False otherwise
        
    BUG: Very basic validation - only checks for @ symbol
    """
    if "@" in email:
        return True
    return False


if __name__ == "__main__":
    # Demo the functions
    print("calculate_average([1, 2, 3, 4, 5]):", calculate_average([1, 2, 3, 4, 5]))
    print("calculate_average([]):", calculate_average([]))
    
    print("\ndivide_numbers(10, 2):", divide_numbers(10, 2))
    # This will crash: divide_numbers(10, 0)
    
    print("\nprocess_data([1, 2, 3]):", process_data([1, 2, 3]))
    # This will crash: process_data(["a", "b"])
    
    print("\nfind_maximum([1, 5, 3, 9, 2]):", find_maximum([1, 5, 3, 9, 2]))  # Returns 1 (wrong!)
    print("find_maximum([10, 20, 5]):", find_maximum([10, 20, 5]))  # Returns 5 (wrong!)
    
    print("\nvalidate_email('test@example.com'):", validate_email("test@example.com"))
    print("validate_email('invalid'):", validate_email("invalid"))

