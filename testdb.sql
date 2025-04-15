CREATE USER testuser WITH PASSWORD 'testpass';

-- Grant all privileges on testdb to testuser
GRANT ALL PRIVILEGES ON DATABASE testdb TO testuser;

-- Create a sample table
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    age INT,
    grade VARCHAR(10)
);

-- Insert sample data
INSERT INTO students (name, age, grade) VALUES
('Alice', 14, 'A'),
('Bob', 15, 'B'),
('Charlie', 13, 'A');

SELECT * FROM students;

SELECT students 
FROM information_schema.tables 
WHERE table_schema = 'public';
