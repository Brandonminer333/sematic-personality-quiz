import ResultsPage from '@/components/ResultsPage';

export default async function ResultsRoute({ params }) {
  const { quizId } = await params;
  return <ResultsPage quizId={quizId} />;
}
