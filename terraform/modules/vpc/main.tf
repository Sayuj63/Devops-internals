###############################################################################
# Module: vpc
# Three-AZ VPC with public + private subnets, 3 NAT gateways, IGW, route tables,
# VPC flow logs to S3, and EKS-discovery subnet tags.
###############################################################################

locals {
  public_subnets  = [for i, az in var.availability_zones : cidrsubnet(var.cidr, 4, i)]
  private_subnets = [for i, az in var.availability_zones : cidrsubnet(var.cidr, 4, i + 8)]
}

resource "aws_vpc" "this" {
  cidr_block           = var.cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(var.tags, { Name = var.name })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = merge(var.tags, { Name = "${var.name}-igw" })
}

resource "aws_subnet" "public" {
  for_each = { for idx, az in var.availability_zones : idx => az }

  vpc_id                  = aws_vpc.this.id
  cidr_block              = local.public_subnets[each.key]
  availability_zone       = each.value
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name                                          = "${var.name}-public-${each.value}"
    "kubernetes.io/role/elb"                      = "1"
    "kubernetes.io/cluster/${var.cluster_name}"   = "shared"
    Tier                                          = "public"
  })
}

resource "aws_subnet" "private" {
  for_each = { for idx, az in var.availability_zones : idx => az }

  vpc_id            = aws_vpc.this.id
  cidr_block        = local.private_subnets[each.key]
  availability_zone = each.value

  tags = merge(var.tags, {
    Name                                          = "${var.name}-private-${each.value}"
    "kubernetes.io/role/internal-elb"             = "1"
    "kubernetes.io/cluster/${var.cluster_name}"   = "shared"
    Tier                                          = "private"
  })
}

resource "aws_eip" "nat" {
  for_each = aws_subnet.public
  domain   = "vpc"
  tags     = merge(var.tags, { Name = "${var.name}-nat-${each.key}" })
}

resource "aws_nat_gateway" "this" {
  for_each      = aws_subnet.public
  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = each.value.id
  depends_on    = [aws_internet_gateway.this]

  tags = merge(var.tags, { Name = "${var.name}-nat-${each.key}" })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  tags   = merge(var.tags, { Name = "${var.name}-public" })
}

resource "aws_route" "public_default" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  for_each       = aws_subnet.public
  route_table_id = aws_route_table.public.id
  subnet_id      = each.value.id
}

resource "aws_route_table" "private" {
  for_each = aws_subnet.private
  vpc_id   = aws_vpc.this.id
  tags     = merge(var.tags, { Name = "${var.name}-private-${each.key}" })
}

resource "aws_route" "private_default" {
  for_each               = aws_route_table.private
  route_table_id         = each.value.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this[each.key].id
}

resource "aws_route_table_association" "private" {
  for_each       = aws_subnet.private
  route_table_id = aws_route_table.private[each.key].id
  subnet_id      = each.value.id
}

###############################################################################
# VPC flow logs → S3
###############################################################################

resource "random_id" "flow_logs_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "flow_logs" {
  bucket        = "${var.name}-vpc-flow-logs-${random_id.flow_logs_suffix.hex}"
  force_destroy = false
  tags          = merge(var.tags, { Name = "${var.name}-flow-logs" })
}

resource "aws_s3_bucket_public_access_block" "flow_logs" {
  bucket                  = aws_s3_bucket.flow_logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "flow_logs" {
  bucket = aws_s3_bucket.flow_logs.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "flow_logs" {
  bucket = aws_s3_bucket.flow_logs.id
  rule {
    id     = "expire"
    status = "Enabled"
    expiration { days = var.flow_logs_retention }
    abort_incomplete_multipart_upload { days_after_initiation = 7 }
  }
}

resource "aws_flow_log" "this" {
  vpc_id               = aws_vpc.this.id
  log_destination      = aws_s3_bucket.flow_logs.arn
  log_destination_type = "s3"
  traffic_type         = "ALL"
  max_aggregation_interval = 60

  tags = merge(var.tags, { Name = "${var.name}-flowlogs" })
}
