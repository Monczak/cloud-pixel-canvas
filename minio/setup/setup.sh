#!/bin/sh
set -e

MINIO_ALIAS="local"
MINIO_URL=${MINIO_URL:-"http://minio:9000"}

echo "Waiting for MinIO at $MINIO_URL..."
until mc alias set $MINIO_ALIAS $MINIO_URL $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD; do
    echo "...waiting..."
    sleep 2
done

echo "MinIO is up. Running setup..."

echo "Creating bucket: pixel-canvas-snapshots"
mc mb --ignore-existing $MINIO_ALIAS/pixel-canvas-snapshots

echo "Setting strict public read policy..."
cat > /tmp/policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": ["*"]},
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::pixel-canvas-snapshots/*"]
    }
  ]
}
EOF

mc anonymous set-json /tmp/policy.json $MINIO_ALIAS/pixel-canvas-snapshots

if [ ! -z "$MINIO_ADMIN_USER" ] && [ ! -z "$MINIO_ADMIN_PASSWORD" ]; then
    echo "Creating admin user: $MINIO_ADMIN_USER"
    mc admin user add $MINIO_ALIAS $MINIO_ADMIN_USER $MINIO_ADMIN_PASSWORD

    echo "Attaching consoleAdmin policy..."
    mc admin policy attach $MINIO_ALIAS consoleAdmin --user $MINIO_ADMIN_USER
else
    echo "Skipping admin user creation (MINIO_ADMIN_USER/PASS not set)"
fi

echo "MinIO setup completed successfully."
