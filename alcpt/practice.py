import json
import random
from collections import OrderedDict

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from .exceptions import IllegalArgumentError, ArgumentError
from .decorators import permission_check, custom_redirect
from .definitions import UserType, QuestionType, ExamType, QuestionTypeCounts
from .models import AnswerSheet, Question, Student, User, Exam, TestPaper
from .managerfuncs import practicemanager


@permission_check(UserType.Testee)
@require_http_methods(["GET", "POST"])
def create(request, practice_type):
    if request.method == 'POST':
        raw_question_types = []
        for question_type in request.POST.get('question_type').split(','):
            if question_type is None or len(question_type) is 0:
                raise IllegalArgumentError('Question type is null.')

            try:
                raw_question_types.append(int(question_type))

            except ValueError:
                raise IllegalArgumentError('Question type must be integer.')

        question_types = []
        for valid_type in [QuestionType.QA, QuestionType.ShortConversation] if practice_type == 'listening' \
                else [QuestionType.Grammar, QuestionType.Phrase, QuestionType.ParagraphUnderstanding]:
            if valid_type.value[0] in raw_question_types:
                question_types.append(valid_type)

        try:
            num_questions = int(request.POST.get('num_questions', 0))

        except TypeError:
            raise ArgumentError('Question amount is null.')

        except ValueError:
            raise IllegalArgumentError('Question amount must be integer.')
        user = User.objects.get(reg_id=request.user.reg_id)
        practice_type = ExamType.Listening if practice_type == 'listening' else ExamType.Reading
        practice, selected_questions = practicemanager.create_practice(user=user, practice_type=practice_type,
                                                                       question_types=question_types, num_questions=num_questions)
        for question in selected_questions:
            question.option = json.loads(question.option)
        data = {
            "practice": practice,
            "practice_type": practice_type.value[1],
            "selected_questions": selected_questions,
        }

        return redirect('/tester/practice/{}/take'.format(practice.id))
        # return render(request, 'practice/show.html', data)
        # return custom_redirect('/tester/practice/{}/take'.format(practice.id), selected_questions=selected_questions)

    else:

        question_types = []

        if practice_type == 'listening':
            question_types.extend([[QuestionType.QA.value[0], 'quora'],
                                   [QuestionType.ShortConversation.value[0], 'comments']])

        elif practice_type == 'reading':
            question_types.extend([[QuestionType.Grammar.value[0], 'pencil-square-o'],
                                   [QuestionType.Phrase.value[0], 'language'],
                                   [QuestionType.ParagraphUnderstanding.value[0], 'book']])

        else:
            raise IllegalArgumentError('Unknow practice type "{}"'.format(practice_type))

        data = {
            'practice_type': practice_type,
            'question_types': question_types,
        }

        return render(request, 'practice/create_practice.html', data)


@permission_check(UserType.Testee)
@require_http_methods(["GET", "POST"])
def create_integration(request):
    practice_type = ExamType.Practice
    question_types = [question_type.value[0] for question_type in QuestionType.__members__.values()]
    num_questions = sum(QuestionTypeCounts.Exam.value[0])
    user = User.objects.get(reg_id=request.user.reg_id)
    practice, selected_questions = practicemanager.create_practice(user=user, practice_type=practice_type,
                                                                   question_types=question_types,
                                                                   num_questions=num_questions,
                                                                   integration=True)

    return redirect('/practice/{}/take'.format(practice.id), selected_questions=selected_questions)


@permission_check(UserType.Testee)
@require_http_methods(["GET", "POST"])
def take_practice(request, practice_id, question_index: int):
    try:
        question_index = int(question_index)
    except ValueError:
        question_index = 0
    try:
        answer_sheet = AnswerSheet.objects.get(exam_id=practice_id, user_id=request.user.id)
        answers = json.loads(answer_sheet.answers)
        questions = json.loads(answer_sheet.questions)
    except ObjectDoesNotExist:
        testpaper = TestPaper.objects.get(id=Exam.objects.get(id=practice_id).testpaper_id)
        selected_questions = list(testpaper.question_set.all())
        answers = OrderedDict((question.id, -1) for question in selected_questions)
        questions = OrderedDict(
            (selected_questions.index(question), (question.id, random.sample(range(4), 4)))
            for question in selected_questions)
        answer_sheet = AnswerSheet.objects.create(exam_id=practice_id,
                                                  user_id=request.user.id,
                                                  questions=json.dumps(questions),
                                                  answers=json.dumps(answers),
                                                  is_finished=0,
                                                  score=0)
    question_num=len(questions)
    answer_num = 0
    question_id = list(answers.items())[question_index][0]
    question = Question.objects.get(id=question_id)
    question_option = json.loads(question.option)

    if request.method == "POST":
        answer = int(request.POST.get('answer-{}'.format(question.id)))

        answers[question_id] = answer
        answer_sheet.answers = json.dumps(answers)
        answer_sheet.save()

        if question_index + 1 < question_num:
            return redirect('/tester/practice/{}/take/{}'.format(practice_id, question_index + 1))
        else:
            answers = json.loads(answer_sheet.answers)
            answer_sheet.finish = True
            answer_sheet.save()

            messages.success(request, "Complete the practice.")

            return redirect('/')
    else:
        question.option = json.loads(question.option)

        data = {
            'answer_sheet': answer_sheet,
            'question_num': question_num,
            'question': question,
            'index': question_index,
            'next' : question_index + 1,
            'has_next': question_index + 1 < question_num,
            'practice_id': practice_id,
            'selected_answered': -1,
            'answers': answers,
            'num_questions': range(answer_num),
        }

        return render(request, 'practice/answer.html', data)


@permission_check(UserType.Testee)
@require_http_methods(["POST"])
def stop_practice(request, question_index, answer_sheet_id):
    try:
        question_index = int(question_index)

    except ValueError:
        question_index = 0

    answer_sheet = AnswerSheet.objects.get(id=answer_sheet_id)
    answers = json.loads(answer_sheet.answers)
    questions = json.loads(answer_sheet.questions)
    answer_num = 0
    for question_id in answers:
        answer_num += 1

    if question_index >= answer_num:
        raise IllegalArgumentError('Question index out of range.')

    else:
        question_id, options = questions[question_index][0]
        question = Question.objects.get(id=question_id)
        question.option = json.loads(question.option)

    try:
        answer = int(request.POST.get('answer-{}'.format(question.id)))

        if answer not in range(len(question.options)):
            raise IllegalArgumentError(message='Invalid answer.')

    except TypeError:
        raise IllegalArgumentError(message='At least one option needs to be selected.')

    answers[question_id] = answer
    answer_sheet.answers = json.dumps(answers)
    answer_sheet.save()

    messages.success(request, "Stop the practice.")

    return redirect('/')