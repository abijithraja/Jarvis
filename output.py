# Program to add two numbers and save the result to a file on the desktop
def add_numbers_and_save(num1, num2):
    result = num1 + num2  # Add the two numbers
    filename = "C:\\Users\\YourUsername\\Desktop\\result.txt"  # Update 'YourUsername' with actual username
    with open(filename, 'w') as file:
        file.write(str(result))  # Write the result to the file

# Example usage
add_numbers_and_save(5, 3)