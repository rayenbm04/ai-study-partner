import { apiRequest } from "./client";
import type { Difficulty, Quiz, QuizAttempt, QuizAttemptResult, QuizListItem, QuestionType } from "./types";

export async function listQuizzesForSubject(subjectId: string): Promise<QuizListItem[]> {
  return apiRequest<QuizListItem[]>(`/api/v1/subjects/${subjectId}/quizzes`);
}

export async function generateQuiz(
  subjectId: string,
  input: {
    document_id: string;
    count?: number;
    difficulty?: Difficulty;
    question_types?: QuestionType[];
    title?: string;
  }
): Promise<Quiz> {
  return apiRequest<Quiz>(`/api/v1/subjects/${subjectId}/quizzes/generate`, { method: "POST", body: input });
}

export async function getQuiz(quizId: string): Promise<Quiz> {
  return apiRequest<Quiz>(`/api/v1/quizzes/${quizId}`);
}

/** Works for both quizzes and exams — an exam is just a Quiz row with
 * kind="exam" (see backend/app/services/exam_engine/exam_service.py). */
export async function deleteQuiz(quizId: string): Promise<void> {
  return apiRequest<void>(`/api/v1/quizzes/${quizId}`, { method: "DELETE" });
}

export async function startAttempt(quizId: string): Promise<QuizAttempt> {
  return apiRequest<QuizAttempt>(`/api/v1/quizzes/${quizId}/attempts`, { method: "POST" });
}

/** Deliberately doesn't return whether the answer was correct — the
 * backend withholds that until the attempt is submitted (see
 * AnswerAckResponse), so the UI shouldn't imply per-question feedback
 * exists here either. */
export async function submitAnswer(
  attemptId: string,
  input: { question_id: string; answer: string; time_spent_seconds?: number }
): Promise<{ question_id: string; submitted_at: string }> {
  return apiRequest(`/api/v1/quiz-attempts/${attemptId}/answers`, { method: "POST", body: input });
}

export async function submitAttempt(attemptId: string): Promise<QuizAttemptResult> {
  return apiRequest<QuizAttemptResult>(`/api/v1/quiz-attempts/${attemptId}/submit`, { method: "POST" });
}
