import { apiRequest } from "./client";
import type { Difficulty, Quiz, QuestionType, QuizAttempt } from "./types";

/** Exams are quizzes with kind="exam" — same attempt/answer/submit routes as
 * a regular quiz (see lib/api/quizzes.ts), generated with exam-specific
 * params (a time limit, a style). */
export async function generateExam(
  subjectId: string,
  input: {
    document_id: string;
    count?: number;
    difficulty?: Difficulty;
    question_types?: QuestionType[];
    duration_minutes?: number;
    style?: string;
    title?: string;
  }
): Promise<Quiz> {
  return apiRequest<Quiz>(`/api/v1/subjects/${subjectId}/exams/generate`, { method: "POST", body: input });
}

export async function getExamHistory(examId: string): Promise<QuizAttempt[]> {
  return apiRequest<QuizAttempt[]>(`/api/v1/exams/${examId}/history`);
}
