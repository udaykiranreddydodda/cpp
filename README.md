# Smart Inventory Management System

A serverless inventory management system built on AWS, designed for tracking products, managing stock levels, and sending automated notifications.

## Tech Stack

**Frontend:** React + Vite, hosted on Amazon S3 (static website hosting)

**Backend:** Python 3.11 AWS Lambda function with API Gateway (REST API)

**Database:** Amazon DynamoDB (on-demand capacity)

**Shared Library:** Python package with common utilities, tested with pytest

## AWS Services

1. **AWS Lambda** - Serverless backend API handling all business logic
2. **Amazon DynamoDB** - NoSQL database for inventory data storage
3. **Amazon S3** - File storage bucket and static frontend hosting
4. **Amazon API Gateway** - REST API with proxy integration and CORS support
5. **Amazon SNS** - Notifications for inventory alerts and updates
6. **AWS IAM** - Role-based access control for Lambda execution

## Features

- Product inventory CRUD operations
- Stock level tracking and management
- File uploads via S3
- Automated notifications via SNS
- JWT-based authentication
- CORS-enabled API for cross-origin access
- Fully automated CI/CD pipeline via GitHub Actions

## Project Structure

```
uday/
├── backend/
│   └── lambda_function.py
├── frontend/
│   └── (React + Vite application)
├── library/
│   └── (Shared Python package with tests)
├── .github/
│   └── workflows/
│       └── deploy.yml
└── README.md
```

## Deployment

The project uses GitHub Actions for CI/CD. Pushing to the `main` branch triggers:

1. **Test** - Runs pytest on the shared library
2. **Deploy Backend** - Provisions AWS resources and deploys the Lambda function
3. **Deploy Frontend** - Builds the React app and deploys to S3

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS access key for deployment |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for deployment |

### Deployed URLs

- **Frontend:** `http://smartinventory-frontend-prod-udaykiran.s3-website-eu-west-1.amazonaws.com`
- **API:** `https://<api-id>.execute-api.eu-west-1.amazonaws.com/prod`
