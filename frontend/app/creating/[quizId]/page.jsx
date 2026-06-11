import CreatingPage from '@/components/CreatingPage';

export default async function CreatingRoute({ params }) {
  const { quizId } = await params;
  return <CreatingPage quizId={quizId} />;
}
