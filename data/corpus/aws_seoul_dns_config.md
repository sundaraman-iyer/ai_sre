# AWS Seoul EC2 DNS resolver incident

Source report: https://aws.amazon.com/message/74876-2/

This corpus record is a fixed summary from the public danluu/post-mortems index.

A configuration change in the Seoul region removed the setting defining the minimum
healthy-host count for the EC2 DNS resolver fleet. The fleet consequently used a very low
default. Its healthy-host count dropped, and in-VPC DNS queries from EC2 instances failed
for approximately 84 minutes until responders manually restored capacity. AWS listed
semantic configuration validation and hourly throttling of host removal as remediations.
