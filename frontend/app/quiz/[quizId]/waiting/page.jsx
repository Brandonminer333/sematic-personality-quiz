import WaitingPage from '@/components/WaitingPage';

export default async function WaitingRoute({ params }) {
  const { quizId } = await params;
  return <WaitingPage quizId={quizId} />;
}
