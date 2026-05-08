# 5XRestaurant (EatEase) - System & AWS Architecture

Dự án 5XRestaurant (EatEase) là một hệ thống web application phục vụ nhà hàng, được thiết kế và triển khai trên hạ tầng điện toán đám mây AWS với tiêu chuẩn kiến trúc hiện đại, khả năng tái sử dụng, bảo mật và vận hành hoàn toàn tự động thông qua Terraform (Infrastructure as Code - IaC).

---

## 1. High-Level Architecture (Kiến trúc Tổng thể)

### 1.1 Khái quát hệ thống
Hệ thống sử dụng kiến trúc phân tán (Distributed Architecture) kết hợp giữa Container hoá và Serverless cho tính năng AI. Frontend được lưu trữ tĩnh phục vụ qua màng lưới toàn cầu (CDN), Backend linh hoạt tự scale trong container phi máy chủ, và các tác vụ AI phân luồng trực tiếp thông qua hàm Lambda.

### 1.2 Data Communication Flow (Luồng Dữ liệu)
1. **User Request (UI/Tĩnh)**: Trình duyệt của khách cầu tài nguyên web (HTML/JS/CSS) → Amazon CloudFront → Nhận file tĩnh an toàn từ S3 Bucket.
2. **API Request (Backend Data)**: Các thao tác nghiệp vụ, đơn hàng, người dùng gọi RESTful API từ Frontend → Chuyển hướng tới API Gateway.
3. **Backend Processing**: API Gateway phân tuyến:
   - Các requests thông thường → **Application Load Balancer (ALB)** → **Amazon ECS Fargate** (Chứa Node.js API).
   - Yêu cầu AI Chat (`/api/bedrock-chat`) → Tự động khởi chạy **AWS Lambda Function** (Serverless).
4. **Database & AI Interaction**:
   - Truy vấn dữ liệu người dùng, Menu, Cart được thực thi từ ECS Fargate tác động lên **Amazon DocumentDB** sâu trong Private VPC.
   - Lambda AI truy xuất **Amazon Bedrock Knowledge Base (RAG)** → Tìm kiếm Vector thông minh từ File hướng dẫn nhà hàng lưu trên S3 → Trích xuất Context gửi vào model ngôn ngữ ưu việt **Claude 3 Haiku** để sinh câu trả lời cho chat box.

### 1.3 System Architecture Diagram (Sơ đồ hệ thống)

```mermaid
graph TD
    subgraph Client
        Browser[Trình duyệt Khách hàng]
    end

    subgraph AWS Cloud/Edge
        CF[Amazon CloudFront]
        APIGW[Amazon API Gateway]
    end

    subgraph VPC - Public Subnets
        ALB[Application Load Balancer]
        NAT[NAT Gateway]
    end

    subgraph VPC - Private Subnets
        ECS[ECS Fargate Tasks - Node.js App]
        DocDB[(Amazon DocumentDB Cluster)]
    end

    subgraph AWS Serverless & External Cloud
        S3_FE[S3 Bucket - Frontend Assets]
        Lambda[AWS Lambda - Bedrock Chat]
        Bedrock[Amazon Bedrock Knowledge Base]
        S3_Docs[S3 - Knowledge Docs]
    end

    %% Flows
    Browser -->|Tải trang UI| CF
    CF -->|Read (w/ OAC)| S3_FE
    
    Browser -->|API Calls| APIGW
    APIGW -->|/api/*| ALB
    ALB -->|Forward 80| ECS
    ECS -->|CRUD Data| DocDB
    ECS -.->|Pull Images via| NAT
    
    APIGW -->|POST /api/bedrock-chat| Lambda
    Lambda -->|RetrieveAndGenerate API| Bedrock
    Bedrock -->|Sync Knowledge| S3_Docs
```

---

## 2. AWS Infrastructure Details (Provisioned by Terraform)

Toàn bộ hạ tầng điện toán đám mây được chia nhỏ thành các Module Terraform giúp tách biệt rủi ro và quản lý theo nguyên tắc Well-Architected.

### 2.1 Networking & Security (`tf/networking`, `tf/security`)
- **Amazon VPC**: Thiết kế Multi-AZ bao gồm dải Public Subnets (dành riêng cho ALB và NAT Gateway phơi sáng với Web) và Private Subnets (Nơi chạy Container và lưu Database tuyệt mật).
- **NAT Gateway**: Đóng vai trò môi giới 1 chiều cho phép hệ thống phi máy chủ (Fargate) kéo ảnh container từ ECR và giao tiếp ngoại tuyến, nhưng tuyệt đối không ai cấu thành truy cập ngược từ mạng ngoài vào Private Subnet.
- **Security Groups (Lớp rào lửa)**: Tuân thủ cấu hình an ninh tầng tầng lớp lớp (Tiered SG). ALB mở cổng 80/443 ra ngoài → ECS Task chỉ nhận lưu lượng từ riêng ALB ID → DocumentDB chỉ cho phép riêng cổng 27017 vào từ định danh của ECS.

### 2.2 Storage & Database (`tf/storage`)
- **Amazon S3**: Lưu trữ ứng dụng React qua cơ chế Block Public Access triệt để (Không cấu hình Website Hosting bừa bãi). Chỉ phân phối duy nhất thông qua CloudFront Origin Access Control (OAC). S3 Bucket này cũng chứa kho tài liệu nhà hàng (Docs) để làm thức ăn cho mô hình AI.
- **Amazon DocumentDB**: Hệ quản trị phi quan hệ phân tán NoSQL cực kì tương thích với MongoDB, được ẩn sâu dưới VPC. Quản lý cấp phép qua **AWS Secrets Manager**, dọn dẹp các hard-code database/password nguy hiểm trong source project.

### 2.3 Compute & Container (`tf/compute`)
- **Amazon ECR**: Lưu trữ toàn bộ các ảnh (Docker Image) đẩy lên tự động thông qua Github/CI/CD (Deploy scripts).
- **Amazon ECS (Fargate Launch Type)**: Chạy hệ sinh thái backend bằng nền tảng Serverless Container. Không phiền phức quản lí Patch máy chủ EC2 — AWS sẽ cấp phát CPU/Memory trực tiếp.
- **API Gateway**: Thành phần tối quan trọng phơi API ra front layer, quy tụ các liên kết từ Fargate và Lambda đồng thời giúp định tuyến khéo léo thông dịch (proxy).

### 2.4 Serverless AI Integration (`tf/lambda`) — Trọng tâm W3
Dự án được ứng dụng tích hợp AI sâu bên trong kiến trúc Cloud Serverless để vượt khỏi việc chèn code trực tiếp Gemini trên Server Node:
- **AWS Lambda Function**: Nhiệm vụ duy nhất chỉ là Handler trò chuyện AI, tránh làm treo và gánh nặng tải của Node.js Backend truyền thống. Khởi chạy trực tiếp từ API Gateway tức thời.
- **Principle of Least Privilege**: IAM Role cấp trọn vẹn chỉ đúng quyền hạn thiết yếu (CloudWatch Log cho chỉ đích thân Log Group, Bedrock Invoke chính định danh Model ARN đó). Hoàn toàn không wildcard bừa bãi nhằm bảo hộ tuyệt đối tài nguyên AWS.
- **Amazon Bedrock (RAG Framework)**: Sở hữu tệp Data nội bộ về thực đơn và các luật nhà hàng bằng S3. Thực thi nghiệp vụ **RAG (Retrieval-Augmented Generation)** để Knowledge Base cào dữ liệu vector tự động, rồi cung cấp context chính xác, tránh việc "ảo giác" (hallucination) cho model `Claude 3 Haiku`.

---
*Dự án đạt chuẩn Production-ready vững chắc với mức độ bảo mật khắt khe, tối ưu hóa lưu lượng và ứng dụng thông minh xu hướng AI đám mây cao nhất trên AWS hiện nay.*
