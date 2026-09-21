type DocumentItem = {
  title: string
  description: string
  fileName: string
}

const DOCUMENTS: DocumentItem[] = [
  {
    title: "Product FAQ",
    description: "Answers to the most common questions about the product.",
    fileName: "product_faq.pdf",
  },
  {
    title: "Warranty Policy",
    description: "Coverage terms and how to make a warranty claim.",
    fileName: "warranty_policy.pdf",
  },
  {
    title: "Refund Policy",
    description: "Eligibility and steps for requesting a refund.",
    fileName: "refund_policy.pdf",
  },
]

function Documents() {
  return (
    <div className="page-documents">
      <h1>Documents</h1>
      <p className="lede">
        Company documents Maya can reference when answering questions.
      </p>

      <div className="doc-panel">
        <h2>Document list</h2>

        {DOCUMENTS.length === 0 && (
          <p className="empty-state">No documents yet.</p>
        )}

        <div className="list-stack">
          {DOCUMENTS.map((doc) => (
            <div key={doc.fileName} className="doc-card">
              <div className="doc-card-info">
                <div className="doc-card-title">{doc.title}</div>
                <div className="doc-card-description">{doc.description}</div>
              </div>

              <a
                className="secondary-button doc-card-download"
                href={`http://localhost:8000/support/documents/${doc.fileName}/`}                download
              >
                Download
              </a>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Documents
