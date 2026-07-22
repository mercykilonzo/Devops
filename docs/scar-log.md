# Scar Log — Service C — Immaculate

## 1. Wrong region set
**Error:** `Could not connect to endpoint URL: https://sts.D.amazonaws.com/`
**Cause:** `aws configure` was answered with `D` instead of `us-west-2`
**Fix:** `aws configure set region us-west-2`
**Lesson:** Always verify region with `aws configure get region` before running any AWS command.

## 2. Terminal lost echo after docker login
**Error:** Typed characters not appearing in terminal
**Cause:** Docker login pipeline left terminal in no-echo mode
**Fix:** `stty echo`
**Lesson:** If terminal stops showing input, `stty sane` resets all terminal settings.

## 3. Wrong execution role name in task definition
**Error:** `AccessDeniedException` on `ecsTaskExecutionRole`
**Cause:** Role in this account is named `ECS-role-195f983e`, not the AWS default name
**Fix:** Updated ARN to `arn:aws:iam::827478161993:role/ECS-role-195f983e`
**Lesson:** Never assume AWS default resource names. Always verify what actually exists in the account.

## 4. Typo in teammate's SG ID
**Error:** `InvalidGroupId.Malformed` on `sg-0455e19278e08wab4`
**Cause:** `w` typed instead of `b` when copying Ushi's SG ID
**Fix:** Corrected to `sg-0455e19278e08bab4`
**Lesson:** Copy-paste SG IDs directly. Never retype them manually.

## 5. Wrong tags — did not match group agreement
**Error:** Tags had `Project=devops-mentorship` and `Owner=Immaculate`
**Cause:** Used assumed values instead of verifying agreed tags with group
**Fix:** Updated all 5 resources to `Project=devops-class` and `Owner=service-c-owner`
**Lesson:** Confirm tag contract with your group before creating any resource.

## 6. ECS task failed to launch — role trust policy missing
**Error:** `ECS was unable to assume role ECS-role-195f983e`
**Cause:** The role trust policy did not include `ecs-tasks.amazonaws.com`
           as a trusted principal. ECS could not assume the role at all.
**Fix:** Robert added `ecs-tasks.amazonaws.com` to the trust relationship.
**Lesson:** IAM roles need two things: trust policy (WHO can assume it)
            and permission policy (WHAT it can do). Both must be correct.

## 7. ECS task cannot reach ECR — network timeout
**Error:** `dial tcp 34.223.x.x:443: i/o timeout`
**Cause:** Task was in a public subnet but `assignPublicIp=DISABLED`.
           Public subnets route outbound traffic through an internet gateway
           which requires a public IP. No NAT Gateway existed in the VPC.
**Fix:** Updated ECS service to `assignPublicIp=ENABLED` to match subnet type.
**Lesson:** Public subnet = ENABLED. Private subnet + NAT Gateway = DISABLED.
            Always check subnet type before choosing assignPublicIp setting.

## 8. ECS role missing ECR permissions — self-resolved
**Error:** `not authorized to perform: ecr:GetAuthorizationToken`
**Cause:** ECS-role-195f983e had a custom policy but was missing
           AmazonECSTaskExecutionRolePolicy which grants ECR pull
           and CloudWatch logging permissions.
**Fix:** Attached the missing policy myself:
           aws iam attach-role-policy \
             --role-name ECS-role-195f983e \
             --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
**Lesson:** A role can exist and be assumable but still have no permissions.
            Trust policy and permission policy are completely separate.

## 9. Health check failing — curl not installed in base image
**Error:** Container UNHEALTHY despite Gunicorn starting correctly.
           Zero request logs appeared even though service was running.
**Cause:** python:3.12-slim does not include curl. The health check
           `curl -f http://localhost:3003/health` failed silently
           because the binary did not exist inside the container.
           ECS marked the container unhealthy and kept replacing it.
**Fix:** Added curl to Dockerfile:
           RUN apt-get update && apt-get install -y --no-install-recommends curl \
               && rm -rf /var/lib/apt/lists/*
         Rebuilt image as sha-curl-fix, registered task definition :2,
         updated ECS service to revision :2.
**Lesson:** Slim base images deliberately exclude tools like curl to reduce
            attack surface. Always install any binary your health check needs.
            Alternative: use a Python-based health check that needs no binary.

## 10. Service B ECS Deployment — Health Check Failure
**Symptom:** Task kept cycling UNHEALTHY — ECS kept replacing it
**Hypothesis 1:** curl not installed in new Dockerfile
**Evidence:** New Dockerfile removed the apt-get install curl step
**Hypothesis 2:** Health check command syntax wrong in JSON
**Evidence:** CMD-SHELL with single quotes inside JSON failed silently
**Cause:** Two issues — no curl in image, and CMD-SHELL quoting problems
**Fix:** Switched to CMD ["python3", "-c", "..."] health check (task def revision 3)
**Lesson:** Always verify health check tool exists in container before deploying.

## 11. ECS Exec failed — missing taskRoleArn
**Error:** `The service couldn't be updated because a valid taskRoleArn
           is not being used`
**Cause:** ECS Exec requires a task role (separate from execution role)
           so the container can call AWS SSM APIs.
**Fix:** Registered new task definition revision with both:
           executionRoleArn: ECS-role-195f983e (pulls image, writes logs)
           taskRoleArn:      ECS-role-195f983e (allows ECS Exec)
**Lesson:** executionRoleArn = what ECS does on your behalf before
            the container starts. taskRoleArn = what the running
            container itself can do in AWS.

## 12. Service Connect DNS name conflict
**Error:** `ClientAlias service-c:3003 is already used by service
           with discovery name service-c`
**Cause:** Service Connect had already registered `service-c` as a
           DNS name in the cluster namespace from a previous deployment.
           Cannot register the same name twice.
**Fix:** Used alternative DNS name `svc-c` for the client alias.
**Lesson:** Service Connect DNS names are registered in a shared
            namespace across the whole cluster. Coordinate naming
            with your group before deploying.

## Resources Created
| Resource | ID / ARN |
|---|---|
| ECR repository | 827478161993.dkr.ecr.us-west-2.amazonaws.com/devops-g4-service-c |
| Image (original) | sha-f62e683 |
| Image (final) | sha-curl-fix |
| Security group | sg-0bdac0f803bbd4fce |
| SG inbound rule (B→C:3003) | sgr-037800b6c24415052 |
| SG outbound rule (C→A:3001) | sgr-0e20a5df861d7eabb |
| CloudWatch log group | /ecs/devops-g4-service-c |
| Task definition :5 (final) | arn:aws:ecs:us-west-2:827478161993:task-definition/devops-g4-service-c:5 |
| ECS service | arn:aws:ecs:us-west-2:827478161993:service/devops-g4-cluster/devops-g4-service-c |
| Private IP (current task) | 172.31.18.142 |

## Final Status
- Task: RUNNING
- Health: HEALTHY
- Port: 3003
- ECS Exec: enabled
- Circuit breaker + rollback: enabled
- Service Connect DNS: svc-c
- Inbound: Service B only (sg-0455e19278e08bab4)
- Outbound: Service A only (sg-061002084678ef54c) on port 3001

## Entry 10 — Pipeline S3 permissions missing
- **Symptom:** CodeBuild failed with AccessDenied on S3 GetObject
- **Hypothesis:** CodeBuild role missing S3 read permissions
- **Evidence:** Error: `s3:GetObject` not authorized on pipeline artifacts bucket
- **Cause:** CodeBuild role had ECR and ECS permissions but no S3 policy
- **Repair:** Attached AmazonS3FullAccess to devops-g4-service-c-codebuild-role
- **Prevention:** Always attach S3 access to CodeBuild roles when using CodePipeline artifact store

## Entry 12 — Circuit breaker rollback test
- **Symptom:** Deployed revision 9 with health check pointing to wrong port 9999
- **Hypothesis:** Circuit breaker would detect failures and roll back automatically
- **Evidence:** Revision 9 rolloutState changed to FAILED, ECS automatically restored revision 5, then updated to revision 8
- **Cause:** Intentional Gate 3B test
- **Repair:** Service restored to revision 8 with correct SERVICE_A_URL and health check on port 3003
- **Prevention:** Always verify health check port matches container port before deploying
