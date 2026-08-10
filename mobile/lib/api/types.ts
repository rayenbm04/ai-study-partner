/** Types mirror the backend's pydantic response schemas field-for-field —
 * see backend/app/api/v1/schemas/*.py. Keep these in sync by hand for now;
 * there's no shared codegen between the two yet. */

export type User = {
  id: string;
  email: string;
  firstname: string;
  lastname: string;
  role: string;
  pseudo: string | null;
  date_of_birth: string | null;
  school_name: string | null;
  academic_level_id: string | null;
  section_id: string | null;
  is_verified: boolean;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type Subject = {
  id: string;
  name: string;
  description: string | null;
  color: string | null;
  icon: string | null;
  created_at: string;
  archived_at: string | null;
  curriculum_subject_id: string | null;
};

export type Country = {
  id: string;
  name: string;
  code: string | null;
  created_at: string;
};

export type EducationSystem = {
  id: string;
  country_id: string;
  name: string;
  created_at: string;
};

export type AcademicLevel = {
  id: string;
  education_system_id: string;
  name: string;
  order_index: number;
  created_at: string;
};

export type Section = {
  id: string;
  academic_level_id: string;
  name: string;
  created_at: string;
};

export type CurriculumSubject = {
  id: string;
  academic_level_id: string;
  section_id: string | null;
  name: string;
  created_at: string;
};

export type SubjectPackApplyResult = {
  created: Subject[];
  skipped_duplicate_names: string[];
};

export type SubjectPackRemoveResult = {
  removed_count: number;
};

export type AppliedSubjectPack = {
  academic_level_id: string;
  section_id: string | null;
  country_name: string;
  education_system_name: string;
  academic_level_name: string;
  section_name: string | null;
  subject_count: number;
  subjects: Subject[];
};

export type QuestionType = "mcq" | "true_false" | "short_answer" | "calculation" | "fill_blank";
export type Difficulty = "easy" | "medium" | "hard";

export type QuizQuestionPublic = {
  id: string;
  type: QuestionType;
  question: string;
  options: string[] | null;
  points: number;
  difficulty: Difficulty;
  concept_id: string | null;
};

export type Quiz = {
  id: string;
  subject_id: string;
  title: string;
  kind: "quiz" | "exam";
  difficulty: Difficulty;
  topics: string[];
  duration_minutes: number | null;
  style: string | null;
  created_at: string;
  questions: QuizQuestionPublic[];
};

export type QuizListItem = {
  id: string;
  subject_id: string;
  title: string;
  kind: "quiz" | "exam";
  difficulty: Difficulty;
  topics: string[];
  duration_minutes: number | null;
  created_at: string;
  question_count: number;
};

export type QuizAttempt = {
  id: string;
  quiz_id: string;
  started_at: string;
  completed_at: string | null;
  score: number | null;
};

export type QuestionResult = {
  question_id: string;
  question: string;
  type: QuestionType;
  student_answer: string | null;
  correct_answer: string;
  explanation: string | null;
  is_correct: boolean | null;
  points: number;
};

export type QuizAttemptResult = {
  id: string;
  quiz_id: string;
  started_at: string;
  completed_at: string | null;
  score: number | null;
  answers: QuestionResult[];
};

export type FlashcardReviewState = {
  ease_factor: number;
  interval_days: number;
  repetitions: number;
  last_grade: number | null;
  last_reviewed_at: string | null;
  next_review_date: string;
};

export type Flashcard = {
  id: string;
  subject_id: string;
  concept_id: string | null;
  question: string;
  answer: string;
  difficulty: Difficulty;
  tags: string[];
  source: "generated" | "manual";
  created_at: string;
  review: FlashcardReviewState | null;
};

export type ConceptMastery = {
  concept_id: string;
  name: string;
  mastery_score: number | null;
  trend: "up" | "down" | "flat" | null;
  children: ConceptMastery[];
};

export type WeakConcept = {
  id: string;
  concept_id: string;
  reason: "repeated_errors" | "slow_response" | "decay";
  confidence: number;
  status: "active" | "resolved";
  detected_at: string;
};

export type StudyPlanItem = {
  id: string;
  subject_id: string;
  concept_id: string | null;
  scheduled_date: string;
  activity_type: "reading" | "flashcards" | "quiz" | "exam";
  duration_minutes: number;
  status: "pending" | "done" | "skipped";
};

export type StudyPlan = {
  id: string;
  name: string;
  exam_date: string | null;
  daily_minutes_available: number;
  status: "active" | "completed" | "archived";
  created_at: string;
  items: StudyPlanItem[];
};

export type SubjectAnalytics = {
  subject_id: string;
  subject_name: string;
  document_count: number;
  flashcard_count: number;
  flashcards_due_count: number;
  quiz_count: number;
  exam_count: number;
  quiz_attempt_count: number;
  average_quiz_score: number | null;
  conversation_count: number;
  average_mastery: number | null;
  weak_concept_count: number;
  concepts_practiced: number;
  concepts_total: number;
};

export type OverviewAnalytics = {
  subject_count: number;
  total_flashcards_due: number;
  subjects: SubjectAnalytics[];
};

export type Citation = {
  document_id: string;
  document_filename: string;
  chunk_id: string;
  page: number | null;
  section_title: string | null;
};

export type Message = {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  citations: Citation[];
  created_at: string;
};

export type Conversation = {
  id: string;
  subject_id: string;
  title: string | null;
  created_at: string;
};

export type SummaryType = "short" | "detailed" | "bullet" | "key_concepts" | "formula_sheet" | "definitions";

export type Summary = {
  id: string;
  document_id: string;
  subject_id: string;
  summary_type: string;
  content: string;
  created_at: string;
  updated_at: string;
};

export type DocumentType = "exam" | "resume" | "td" | "tp" | "cours" | "other";

export type Document = {
  id: string;
  subject_id: string;
  original_filename: string;
  file_type: string;
  status: "pending" | "processing" | "ready" | "failed";
  page_count: number | null;
  error_message: string | null;
  uploaded_at: string;
  document_type: DocumentType | null;
  chapter_id: string | null;
  lesson_id: string | null;
  classification_confidence: number | null;
  classified_at: string | null;
};
