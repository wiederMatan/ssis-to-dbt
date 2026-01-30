-- Create sample database for SSIS-to-dbt migration testing
CREATE DATABASE SalesDB;
GO

USE SalesDB;
GO

-- Source tables (simulating SSIS source data)
CREATE TABLE dbo.Customers (
    CustomerID INT PRIMARY KEY,
    CustomerName NVARCHAR(100),
    Email NVARCHAR(255),
    Region NVARCHAR(50),
    CreatedDate DATETIME DEFAULT GETDATE(),
    ModifiedDate DATETIME DEFAULT GETDATE()
);

CREATE TABLE dbo.Products (
    ProductID INT PRIMARY KEY,
    ProductName NVARCHAR(100),
    Category NVARCHAR(50),
    UnitPrice DECIMAL(10,2),
    IsActive BIT DEFAULT 1
);

CREATE TABLE dbo.Orders (
    OrderID INT PRIMARY KEY,
    CustomerID INT,
    OrderDate DATETIME,
    TotalAmount DECIMAL(12,2),
    Status NVARCHAR(20)
);

CREATE TABLE dbo.OrderDetails (
    OrderDetailID INT PRIMARY KEY,
    OrderID INT,
    ProductID INT,
    Quantity INT,
    UnitPrice DECIMAL(10,2),
    Discount DECIMAL(5,2) DEFAULT 0
);

-- Insert sample data
INSERT INTO dbo.Customers (CustomerID, CustomerName, Email, Region) VALUES
(1, 'Acme Corp', 'contact@acme.com', 'North'),
(2, 'TechStart Inc', 'info@techstart.com', 'South'),
(3, 'Global Retail', 'sales@globalretail.com', 'East'),
(4, 'DataDriven LLC', 'hello@datadriven.com', 'West');

INSERT INTO dbo.Products (ProductID, ProductName, Category, UnitPrice) VALUES
(101, 'Widget A', 'Electronics', 29.99),
(102, 'Widget B', 'Electronics', 49.99),
(103, 'Service Pack', 'Services', 199.99),
(104, 'Premium Support', 'Services', 499.99);

INSERT INTO dbo.Orders (OrderID, CustomerID, OrderDate, TotalAmount, Status) VALUES
(1001, 1, '2024-01-15', 299.90, 'Completed'),
(1002, 2, '2024-01-16', 649.97, 'Completed'),
(1003, 1, '2024-01-20', 199.99, 'Pending'),
(1004, 3, '2024-01-22', 999.98, 'Shipped');

INSERT INTO dbo.OrderDetails (OrderDetailID, OrderID, ProductID, Quantity, UnitPrice, Discount) VALUES
(1, 1001, 101, 10, 29.99, 0),
(2, 1002, 102, 5, 49.99, 0),
(3, 1002, 103, 2, 199.99, 0),
(4, 1003, 103, 1, 199.99, 0),
(5, 1004, 104, 2, 499.99, 0);

PRINT 'SalesDB created with sample data';
GO
