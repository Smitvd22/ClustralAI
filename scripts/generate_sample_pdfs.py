#!/usr/bin/env python3
# =============================================================================
# Generate Sample PDFs for Testing
# =============================================================================
"""
Generates 5 sample PDF documents with realistic content for
testing the RAG system's ingestion, retrieval, and citation features.

Usage:
    pip install fpdf2
    python scripts/generate_sample_pdfs.py

Output: sample_pdfs/ directory with 5 PDF files.
"""
import os
from fpdf import FPDF


def create_pdf(filename: str, title: str, chapters: list[dict[str, str]]) -> None:
    """Create a multi-page PDF with structured content."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    for chapter in chapters:
        pdf.add_page()
        pdf.set_font("Helvetica", style="B", size=16)
        pdf.cell(0, 10, chapter["title"], new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 7, chapter["content"])

    os.makedirs("sample_pdfs", exist_ok=True)
    filepath = os.path.join("sample_pdfs", filename)
    pdf.output(filepath)
    print(f"  Created: {filepath} ({len(chapters)} pages)")


def main() -> None:
    print("Generating sample PDFs for testing...\n")

    # --- PDF 1: Employee Handbook ---
    create_pdf("employee_handbook.pdf", "Employee Handbook", [
        {
            "title": "Chapter 1: Company Overview",
            "content": (
                "Acme Corporation was founded in 1995 and is headquartered in San Francisco, "
                "California. The company specializes in enterprise software solutions with a focus "
                "on cloud computing and artificial intelligence. Acme employs over 2,500 people "
                "across 12 offices worldwide. Our mission is to empower businesses through "
                "innovative technology solutions that drive growth and efficiency.\n\n"
                "The company operates in three main business segments: Cloud Services, AI Solutions, "
                "and Enterprise Consulting. Annual revenue exceeded $500 million in fiscal year 2025."
            ),
        },
        {
            "title": "Chapter 2: Employee Benefits",
            "content": (
                "Full-time employees are eligible for comprehensive benefits starting on their "
                "first day of employment. Benefits include medical, dental, and vision insurance "
                "with 80% employer contribution. The company provides a 401(k) retirement plan "
                "with 4% employer match. Employees receive 20 days of paid time off per year, "
                "increasing to 25 days after 5 years. Sick leave is provided at 10 days per year.\n\n"
                "Additional benefits include annual education stipend of $5,000, home office "
                "allowance of $1,000, gym membership reimbursement up to $100/month, and employee "
                "stock purchase plan at 15% discount."
            ),
        },
        {
            "title": "Chapter 3: Code of Conduct",
            "content": (
                "All employees must adhere to the highest ethical standards. Conflicts of interest "
                "must be disclosed to the Ethics Committee within 5 business days. Gifts from vendors "
                "exceeding $50 in value must be reported. Insider trading is strictly prohibited.\n\n"
                "Harassment of any kind, including verbal, physical, and digital, will result in "
                "immediate disciplinary action up to and including termination. The company maintains "
                "a zero-tolerance policy for discrimination based on race, gender, age, religion, "
                "disability, or sexual orientation."
            ),
        },
    ])

    # --- PDF 2: Security Policy ---
    create_pdf("security_policy.pdf", "Information Security Policy", [
        {
            "title": "Section 1: Access Control",
            "content": (
                "Access to company systems is governed by the principle of least privilege. "
                "All access requests must be approved by the employee's direct manager and the "
                "IT Security team. Access reviews are conducted quarterly. Privileged accounts "
                "require additional approval from the CISO.\n\n"
                "Multi-factor authentication (MFA) is mandatory for all systems. Passwords must "
                "be at least 14 characters and include uppercase, lowercase, numbers, and symbols. "
                "Passwords expire every 90 days. Password reuse is prohibited for the last 12 passwords."
            ),
        },
        {
            "title": "Section 2: Data Classification",
            "content": (
                "Data is classified into four levels: Public, Internal, Confidential, and Restricted. "
                "Public data may be freely shared. Internal data is for employee use only. "
                "Confidential data requires encryption at rest and in transit. Restricted data "
                "requires additional access controls and audit logging.\n\n"
                "Customer data is always classified as Confidential at minimum. Financial records "
                "and healthcare data are classified as Restricted. All data must be labeled according "
                "to its classification level."
            ),
        },
        {
            "title": "Section 3: Incident Response",
            "content": (
                "Security incidents must be reported to the Security Operations Center (SOC) within "
                "1 hour of discovery. The incident response process follows four phases: "
                "Identification, Containment, Eradication, and Recovery.\n\n"
                "Critical incidents affecting customer data must be escalated to the CISO and "
                "Legal team immediately. Affected customers must be notified within 72 hours as "
                "required by applicable data protection regulations. Post-incident reviews are "
                "conducted within 5 business days of resolution."
            ),
        },
    ])

    # --- PDF 3: Product Documentation ---
    create_pdf("product_guide.pdf", "Product User Guide", [
        {
            "title": "Getting Started",
            "content": (
                "Welcome to Acme Cloud Platform. This guide covers installation, configuration, "
                "and basic usage of the platform. System requirements: 4 GB RAM minimum, 20 GB "
                "disk space, and a supported operating system (Windows 10+, macOS 12+, or Ubuntu 20.04+).\n\n"
                "To install, download the installer from the customer portal at portal.acme.com. "
                "Run the installer with administrator privileges. The installation process takes "
                "approximately 10 minutes. After installation, launch the application and sign in "
                "with your company credentials."
            ),
        },
        {
            "title": "Dashboard Overview",
            "content": (
                "The main dashboard provides a real-time overview of your cloud resources. "
                "The left panel shows resource categories: Compute, Storage, Networking, and Security. "
                "The center panel displays resource utilization metrics with customizable time ranges.\n\n"
                "Key metrics displayed include CPU utilization, memory usage, network throughput, "
                "and storage consumption. Alerts can be configured for any metric threshold. "
                "The dashboard supports custom layouts and can be shared with team members."
            ),
        },
    ])

    # --- PDF 4: Financial Policy ---
    create_pdf("financial_policy.pdf", "Financial Policies and Procedures", [
        {
            "title": "Expense Reporting",
            "content": (
                "All business expenses must be submitted through the ExpenseTracker system within "
                "30 days of incurrence. Receipts are required for all expenses over $25. "
                "Manager approval is required for expenses over $500. VP approval is required "
                "for expenses over $5,000.\n\n"
                "Travel expenses follow the company travel policy. Economy class is standard for "
                "flights under 6 hours. Hotel reimbursement is capped at $250/night for domestic "
                "travel and $350/night for international travel. Meal per diem is $75/day domestic "
                "and $100/day international."
            ),
        },
        {
            "title": "Procurement",
            "content": (
                "All purchases over $10,000 require a formal procurement process including "
                "competitive bidding from at least three vendors. Purchase orders must be approved "
                "by the department head and Finance. Contracts exceeding $100,000 require Legal review.\n\n"
                "Vendor payments are processed on Net-30 terms unless otherwise negotiated. "
                "Early payment discounts should be taken when the discount exceeds 1%. "
                "All vendors must complete a security assessment before onboarding."
            ),
        },
    ])

    # --- PDF 5: Refund and Return Policy ---
    create_pdf("refund_policy.pdf", "Customer Refund and Return Policy", [
        {
            "title": "General Refund Policy",
            "content": (
                "Acme Corporation offers a 30-day money-back guarantee on all software licenses. "
                "Customers may request a full refund within 30 days of purchase for any reason. "
                "After 30 days, refunds are issued at the discretion of customer support management.\n\n"
                "To request a refund, customers should contact support at support@acme.com or "
                "call 1-800-ACME-HELP. Refund requests must include the order number, purchase date, "
                "and reason for the refund. Refunds are processed within 5-7 business days and "
                "credited to the original payment method."
            ),
        },
        {
            "title": "Subscription Cancellation",
            "content": (
                "Subscription services can be cancelled at any time through the account settings "
                "page or by contacting customer support. Cancellations take effect at the end of "
                "the current billing period. No partial-month refunds are provided.\n\n"
                "Annual subscription customers who cancel within the first 60 days receive a "
                "prorated refund for the remaining months. After 60 days, no refund is provided "
                "but the service remains active until the subscription period ends. "
                "Enterprise customers with custom agreements should refer to their contract terms."
            ),
        },
        {
            "title": "Hardware Returns",
            "content": (
                "Hardware products may be returned within 14 days of delivery in original packaging. "
                "Products must be in new condition with all accessories included. A 15% restocking "
                "fee applies to hardware returns unless the product is defective.\n\n"
                "Defective hardware is covered under the 2-year manufacturer warranty. Warranty "
                "claims require proof of purchase and a description of the defect. Replacement "
                "products are shipped within 3-5 business days after the warranty claim is approved. "
                "Shipping costs for warranty replacements are covered by Acme Corporation."
            ),
        },
    ])

    print("\nDone! 5 sample PDFs created in sample_pdfs/ directory.")
    print("Use these with the /ingest endpoint for testing.")


if __name__ == "__main__":
    main()
