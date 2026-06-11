import QuizPage from '@/components/QuizPage';

export default async function QuizRoute({ params }) {
  const { quizId } = await params;
  return <QuizPage quizId={quizId} />;
}
