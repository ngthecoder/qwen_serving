resource "aws_ecr_repository" "ecr_repo" {
  name                 = "${var.project_name}-ecr-repo"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "ecr_policy" {
  repository = aws_ecr_repository.ecr_repo.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only 5 images"
        selection = {
          countType   = "imageCountMoreThan"
          countNumber = 5
          tagStatus   = "any"
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
