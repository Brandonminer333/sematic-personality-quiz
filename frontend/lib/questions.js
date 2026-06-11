// Canonical source: shared/questions.json (bundled copy in questions.data.json).
import questionsData from './questions.data.json';

const LIKERT_VALUES = {
  'strongly disagree': -1.0,
  'somewhat disagree': -0.5,
  neutral: 0.0,
  'somewhat agree': 0.5,
  'strongly agree': 1.0,
};

const { questions, likert_options: likertOptions } = questionsData;

export const QUESTION_COUNT = questions.length;

export const quizQuestions = questions.map((text) => ({ text }));

export const answerOptions = likertOptions.map((text) => ({
  text,
  value: LIKERT_VALUES[text],
}));
