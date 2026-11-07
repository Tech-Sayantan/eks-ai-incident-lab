import {
  to = aws_route53_zone.orders
  id = "Z05270963IBB8NQWWGL52"
}

import {
  to = aws_acm_certificate.orders
  id = "arn:aws:acm:ap-south-1:923988301700:certificate/afbe219e-40f6-4933-bcf8-7b9ed6c095c0"
}

import {
  to = aws_route53_record.certificate_validation
  id = "Z05270963IBB8NQWWGL52__a0ac8d7b2a2b80383a0f6d0f26c5a0e2.orders.tanscape.online_CNAME"
}

import {
  to = aws_route53_record.orders_alias
  id = "Z05270963IBB8NQWWGL52_orders.tanscape.online_A"
}
