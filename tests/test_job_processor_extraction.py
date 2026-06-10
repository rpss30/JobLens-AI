from src.processing.job_processor import extract_skills


def test_extract_skills_detects_database_and_backend_terms():
    description = (
        "The role requires experience with Python, REST APIs, PostgreSQL, "
        "MySQL, Docker, and AWS."
    )

    skills = {skill.lower() for skill in extract_skills(description)}

    assert "python" in skills
    assert "rest apis" in skills
    assert "postgresql" in skills
    assert "mysql" in skills
    assert "docker" in skills
    assert "aws" in skills


def test_extract_skills_detects_ml_and_data_terms():
    description = (
        "Build machine learning models using PyTorch, TensorFlow, scikit-learn, "
        "Pandas, NumPy, MLflow, and model deployment workflows."
    )

    skills = {skill.lower() for skill in extract_skills(description)}

    assert "machine learning" in skills
    assert "pytorch" in skills
    assert "tensorflow" in skills
    assert "scikit-learn" in skills
    assert "pandas" in skills
    assert "numpy" in skills
    assert "mlflow" in skills
    assert "model deployment" in skills


def test_extract_skills_detects_cloud_terms():
    description = (
        "Work with AWS services including EC2, S3, Lambda, API Gateway, "
        "CloudWatch, Terraform, Kubernetes, and CI/CD pipelines."
    )

    skills = {skill.lower() for skill in extract_skills(description)}

    assert "aws" in skills
    assert "ec2" in skills
    assert "s3" in skills
    assert "lambda" in skills
    assert "api gateway" in skills
    assert "cloudwatch" in skills
    assert "terraform" in skills
    assert "kubernetes" in skills
    assert "ci/cd" in skills