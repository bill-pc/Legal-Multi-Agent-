// ============================================================
// Neo4j Schema cho Hệ thống Trợ lý Pháp lý Việt Nam
// Theo NCKH Chương 4.5 – Ontology / Schema Design
// ============================================================

// ---------- Constraints & Indexes ----------

CREATE CONSTRAINT document_id IF NOT EXISTS
FOR (d:Document) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT article_id IF NOT EXISTS
FOR (a:Article) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT clause_id IF NOT EXISTS
FOR (c:Clause) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT point_id IF NOT EXISTS
FOR (p:Point) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT chapter_id IF NOT EXISTS
FOR (ch:Chapter) REQUIRE ch.id IS UNIQUE;

CREATE CONSTRAINT precedent_id IF NOT EXISTS
FOR (pr:Precedent) REQUIRE pr.id IS UNIQUE;

CREATE INDEX document_title IF NOT EXISTS FOR (d:Document) ON (d.title);
CREATE INDEX document_type IF NOT EXISTS FOR (d:Document) ON (d.type);
CREATE INDEX document_status IF NOT EXISTS FOR (d:Document) ON (d.status);
CREATE INDEX article_number IF NOT EXISTS FOR (a:Article) ON (a.number);


// ---------- Node Types (Ontology) ----------
// Document, Chapter, Article, Clause, Point, Precedent, LegalConcept

// Ví dụ tạo Document
// CREATE (d:Document {
//   id: "LUAT-DN-2020",
//   title: "Luật Doanh nghiệp 2020",
//   type: "Luật",
//   issuer: "Quốc hội",
//   effective_date: date("2021-01-01"),
//   status: "Còn hiệu lực"
// })

// ---------- Relationship Types ----------
// Structural Hierarchy:
//   Document -[:HAS_CHAPTER]-> Chapter
//   Chapter  -[:HAS_ARTICLE]-> Article
//   Article  -[:HAS_CLAUSE]-> Clause
//   Clause   -[:HAS_POINT]-> Point
//
// Cross-Reference & Validity:
//   AMENDED_BY   : được sửa đổi bởi
//   REPLACES     : thay thế
//   GUIDES       : hướng dẫn thi hành
//   CITES        : dẫn chiếu
//   APPLIED_IN   : án lệ áp dụng điều khoản


// ---------- Sample data (demo) ----------

// Luật Doanh nghiệp 2020 – Điều 15
MERGE (doc:Document {
  id: "LUAT-DN-2020",
  title: "Luật Doanh nghiệp số 59/2020/QH14",
  type: "Luật",
  issuer: "Quốc hội",
  effective_date: date("2021-01-01"),
  status: "Còn hiệu lực"
})

MERGE (art15:Article {
  id: "LUAT-DN-2020-DIEU-15",
  number: "15",
  title: "Quyền của doanh nghiệp",
  content: "Doanh nghiệp có quyền tự do kinh doanh trong những ngành, nghề mà luật không cấm..."
})

MERGE (doc)-[:HAS_ARTICLE]->(art15)

MERGE (cl1:Clause {
  id: "LUAT-DN-2020-DIEU-15-KHOAN-1",
  number: "1",
  content: "Tự do kinh doanh trong những ngành, nghề mà luật không cấm."
})
MERGE (art15)-[:HAS_CLAUSE]->(cl1)

MERGE (cl2:Clause {
  id: "LUAT-DN-2020-DIEU-15-KHOAN-2",
  number: "2",
  content: "Tự chủ kinh doanh và lựa chọn hình thức tổ chức kinh doanh..."
})
MERGE (art15)-[:HAS_CLAUSE]->(cl2)

RETURN "Schema + sample data created successfully" AS status;
