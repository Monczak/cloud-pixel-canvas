data "archive_file" "snapshot_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/snapshot_scheduler.py"
  output_path = "${path.module}/lambda/snapshot_scheduler.zip"
}

resource "aws_lambda_function" "snapshot_scheduler" {
  filename         = data.archive_file.snapshot_lambda_zip.output_path
  function_name    = "${var.project_name}-snapshot-scheduler"
  role             = var.lab_role_arn
  handler          = "snapshot_scheduler.handler"
  source_code_hash = data.archive_file.snapshot_lambda_zip.output_base64sha256

  runtime = "python3.13"
  timeout = 30

  environment {
    variables = {
      API_URL    = "http://${aws_lb.main.dns_name}"
      SYSTEM_KEY = random_password.system_key.result
    }
  }
}

resource "aws_cloudwatch_event_rule" "snapshot_schedule" {
  name                = "${var.project_name}-snapshot-schedule"
  description         = "Schedule for canvas snapshots"
  schedule_expression = var.snapshot_schedule_expression
}

resource "aws_cloudwatch_event_target" "trigger_lambda" {
  rule      = aws_cloudwatch_event_rule.snapshot_schedule.name
  target_id = "SendToLambda"
  arn       = aws_lambda_function.snapshot_scheduler.arn
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.snapshot_scheduler.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.snapshot_schedule.arn
}
