resource "aws_dynamodb_table" "canvas_state" {
  name         = "${var.project_name}-canvas-state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "canvas_id"

  attribute {
    name = "canvas_id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "snapshots" {
  name         = "${var.project_name}-snapshots"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "snapshot_id"

  attribute {
    name = "snapshot_id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "snapshot_tiles" {
  name         = "${var.project_name}-snapshot-tiles"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "snapshot_id"
  range_key    = "tile_id"

  attribute {
    name = "snapshot_id"
    type = "S"
  }

  attribute {
    name = "tile_id"
    type = "S"
  }
}
