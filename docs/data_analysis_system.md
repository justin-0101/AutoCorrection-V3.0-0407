# 数据分析系统设计

## 1. 概述

数据分析系统是作文批改平台的智能分析模块，负责处理用户作文数据，生成洞察报告，提供个性化学习建议。本文档详细描述了数据分析系统的设计和功能实现。

## 2. 系统架构

数据分析系统主要包含以下组件：
- 数据收集层：收集用户作文和批改数据
- 数据处理层：清洗、转换和存储数据
- 分析算法层：实现各类分析算法
- 可视化层：生成图表和报告
- API接口层：提供数据访问接口

## 3. 数据模型

### 3.1 作文统计模型

```python
class EssayStatistics(db.Model):
    """作文统计数据模型"""
    __tablename__ = 'essay_statistics'
    
    id = db.Column(db.Integer, primary_key=True)
    essay_id = db.Column(db.Integer, db.ForeignKey('essays.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 词汇统计
    word_count = db.Column(db.Integer, default=0)  # 总词数
    unique_word_count = db.Column(db.Integer, default=0)  # 不重复词数
    sentence_count = db.Column(db.Integer, default=0)  # 句子数
    avg_sentence_length = db.Column(db.Float, default=0)  # 平均句长
    
    # 错误统计
    spelling_errors = db.Column(db.Integer, default=0)  # 拼写错误
    grammar_errors = db.Column(db.Integer, default=0)  # 语法错误
    punctuation_errors = db.Column(db.Integer, default=0)  # 标点错误
    word_choice_errors = db.Column(db.Integer, default=0)  # 词语选择错误
    structure_errors = db.Column(db.Integer, default=0)  # 结构错误
    
    # 评分数据
    content_score = db.Column(db.Float)  # 内容得分
    organization_score = db.Column(db.Float)  # 组织得分
    language_score = db.Column(db.Float)  # 语言得分
    overall_score = db.Column(db.Float)  # 总体得分
    
    # 复杂度指标
    readability_score = db.Column(db.Float)  # 可读性分数
    lexical_diversity = db.Column(db.Float)  # 词汇多样性
    syntactic_complexity = db.Column(db.Float)  # 句法复杂度
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联
    essay = db.relationship('Essay', backref='statistics')
```

### 3.2 用户进步追踪模型

```python
class UserProgressTracking(db.Model):
    """用户进步追踪模型"""
    __tablename__ = 'user_progress_tracking'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 记录周期
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    
    # 总体进步指标
    essays_submitted = db.Column(db.Integer, default=0)  # 提交作文数
    avg_overall_score = db.Column(db.Float)  # 平均总分
    score_change = db.Column(db.Float)  # 分数变化
    
    # 各项能力进步
    content_improvement = db.Column(db.Float)  # 内容提升
    organization_improvement = db.Column(db.Float)  # 组织提升
    language_improvement = db.Column(db.Float)  # 语言提升
    
    # 错误减少情况
    spelling_improvement = db.Column(db.Float)  # 拼写提升
    grammar_improvement = db.Column(db.Float)  # 语法提升
    
    # 学习建议
    improvement_areas = db.Column(db.Text)  # JSON格式存储的提升建议
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

## 4. 分析算法

### 4.1 作文统计分析

```python
class EssayAnalytics:
    """作文分析工具类"""
    
    def __init__(self, user_id):
        self.user_id = user_id
    
    def analyze_progress(self, period=30):
        """
        分析用户在指定时间段内的进步情况
        
        Args:
            period: 分析周期(天)
            
        Returns:
            dict: 进步分析结果
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period)
        
        # 获取用户在该时间段内的作文
        essays = Essay.query.filter(
            Essay.user_id == self.user_id,
            Essay.submission_time.between(start_date, end_date),
            Essay.status == 'completed'
        ).order_by(Essay.submission_time).all()
        
        if not essays or len(essays) < 2:
            return {
                'status': 'insufficient_data',
                'message': '数据不足，无法生成进步报告'
            }
        
        # 获取作文统计数据
        statistics = []
        for essay in essays:
            if hasattr(essay, 'statistics') and essay.statistics:
                statistics.append(essay.statistics[0])
        
        # 分析各项指标变化
        first_stats = statistics[0]
        last_stats = statistics[-1]
        
        # 计算进步指标
        progress = {
            'period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
                'days': period
            },
            'essays_count': len(essays),
            'overall_score': {
                'first': first_stats.overall_score,
                'last': last_stats.overall_score,
                'change': last_stats.overall_score - first_stats.overall_score,
                'change_percent': ((last_stats.overall_score - first_stats.overall_score) / 
                                  first_stats.overall_score * 100) if first_stats.overall_score else 0
            },
            'error_reduction': {
                'spelling': self._calculate_change(first_stats.spelling_errors, last_stats.spelling_errors, True),
                'grammar': self._calculate_change(first_stats.grammar_errors, last_stats.grammar_errors, True),
                'punctuation': self._calculate_change(first_stats.punctuation_errors, last_stats.punctuation_errors, True),
                'word_choice': self._calculate_change(first_stats.word_choice_errors, last_stats.word_choice_errors, True)
            },
            'skill_improvement': {
                'content': self._calculate_change(first_stats.content_score, last_stats.content_score),
                'organization': self._calculate_change(first_stats.organization_score, last_stats.organization_score),
                'language': self._calculate_change(first_stats.language_score, last_stats.language_score)
            },
            'complexity_change': {
                'readability': self._calculate_change(first_stats.readability_score, last_stats.readability_score),
                'lexical_diversity': self._calculate_change(first_stats.lexical_diversity, last_stats.lexical_diversity),
                'syntactic_complexity': self._calculate_change(first_stats.syntactic_complexity, last_stats.syntactic_complexity)
            }
        }
        
        # 生成改进建议
        progress['suggestions'] = self._generate_suggestions(progress)
        
        return {
            'status': 'success',
            'data': progress
        }
    
    def _calculate_change(self, first_value, last_value, is_error=False):
        """计算变化率，对于错误指标，减少为正向"""
        if first_value is None or last_value is None:
            return {
                'first': first_value,
                'last': last_value,
                'change': 0,
                'change_percent': 0
            }
        
        change = last_value - first_value
        # 对于错误，减少时给出正向的进步百分比
        if is_error:
            change = -change
        
        change_percent = (change / first_value * 100) if first_value else 0
        
        return {
            'first': first_value,
            'last': last_value,
            'change': change,
            'change_percent': change_percent
        }
    
    def _generate_suggestions(self, progress):
        """根据进步情况生成改进建议"""
        suggestions = []
        
        # 分析各项分数变化，找出最弱项
        skill_changes = progress['skill_improvement']
        sorted_skills = sorted(skill_changes.items(), key=lambda x: x[1]['change_percent'])
        weakest_skill = sorted_skills[0][0]
        
        # 根据最弱项生成建议
        if weakest_skill == 'content':
            suggestions.append({
                'area': 'content',
                'title': '内容丰富度提升',
                'description': '尝试在作文中加入更多相关的例子和细节，以增强内容的丰富度和说服力。'
            })
        elif weakest_skill == 'organization':
            suggestions.append({
                'area': 'organization',
                'title': '文章结构优化',
                'description': '注意段落之间的逻辑连接，使用适当的过渡词，确保文章结构清晰有序。'
            })
        elif weakest_skill == 'language':
            suggestions.append({
                'area': 'language',
                'title': '语言表达提升',
                'description': '尝试使用更多高级词汇和复杂句式，但确保正确使用，避免过度复杂导致表达不清。'
            })
        
        # 分析错误情况，找出最常见的错误类型
        error_changes = progress['error_reduction']
        sorted_errors = sorted(error_changes.items(), key=lambda x: x[1]['last'], reverse=True)
        most_common_error = sorted_errors[0][0]
        
        # 根据最常见错误类型生成建议
        if most_common_error == 'spelling':
            suggestions.append({
                'area': 'spelling',
                'title': '拼写错误减少',
                'description': '建议使用拼写检查工具，并对常拼错的单词进行专项记忆。'
            })
        elif most_common_error == 'grammar':
            suggestions.append({
                'area': 'grammar',
                'title': '语法错误减少',
                'description': '注意动词时态一致性和主谓一致，复习常见语法规则。'
            })
        
        return suggestions
```

## 5. API接口设计

### 5.1 用户进步分析接口

```python
@analysis_bp.route('/progress', methods=['GET'])
@login_required
def get_progress_analysis():
    """获取用户进步分析报告"""
    # 获取分析周期参数，默认30天
    period = request.args.get('period', 30, type=int)
    
    # 创建分析实例
    analytics = EssayAnalytics(g.user.id)
    
    # 获取进步分析结果
    result = analytics.analyze_progress(period)
    
    return jsonify(result)
```

### 5.2 作文错误分布接口

```python
@analysis_bp.route('/error-distribution', methods=['GET'])
@login_required
def get_error_distribution():
    """获取用户作文错误分布情况"""
    # 获取时间范围参数
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # 如果没有指定时间范围，使用最近3个月
    if not start_date:
        start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # 转换为datetime对象
    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
    end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    
    # 查询该时间段内用户的作文统计
    stats = EssayStatistics.query.join(Essay).filter(
        EssayStatistics.user_id == g.user.id,
        Essay.submission_time.between(start_datetime, end_datetime)
    ).all()
    
    if not stats:
        return jsonify({
            'status': 'error',
            'message': '该时间段内暂无数据'
        })
    
    # 计算错误分布
    error_types = ['spelling_errors', 'grammar_errors', 'punctuation_errors', 
                  'word_choice_errors', 'structure_errors']
    
    error_distribution = {
        'labels': ['拼写错误', '语法错误', '标点错误', '词语选择错误', '结构错误'],
        'datasets': []
    }
    
    # 汇总数据
    total_errors = {error_type: 0 for error_type in error_types}
    error_by_essay = []
    
    for stat in stats:
        essay_errors = {}
        for error_type in error_types:
            error_count = getattr(stat, error_type, 0) or 0
            total_errors[error_type] += error_count
            essay_errors[error_type] = error_count
        
        error_by_essay.append({
            'essay_id': stat.essay_id,
            'date': Essay.query.get(stat.essay_id).submission_time.strftime('%Y-%m-%d'),
            'errors': essay_errors
        })
    
    # 添加总体数据
    error_distribution['datasets'].append({
        'label': '总体错误分布',
        'data': [total_errors[error_type] for error_type in error_types]
    })
    
    # 计算随时间变化情况
    error_distribution['time_series'] = {
        'labels': [item['date'] for item in error_by_essay],
        'datasets': []
    }
    
    for i, error_type in enumerate(error_types):
        error_distribution['time_series']['datasets'].append({
            'label': error_distribution['labels'][i],
            'data': [item['errors'][error_type] for item in error_by_essay]
        })
    
    return jsonify({
        'status': 'success',
        'data': {
            'error_distribution': error_distribution,
            'period': {
                'start_date': start_date,
                'end_date': end_date
            }
        }
    })
```

### 5.3 评分趋势接口

```python
@analysis_bp.route('/score-trend', methods=['GET'])
@login_required
def get_score_trend():
    """获取用户评分趋势"""
    # 实现详细代码...
```

## 6. 数据处理流程

### 6.1 作文批改后的统计处理

```python
@shared_task(name='tasks.analysis_tasks.process_essay_statistics')
def process_essay_statistics(essay_id):
    """处理作文统计数据任务"""
    try:
        # 获取作文信息
        essay = Essay.query.get(essay_id)
        if not essay or essay.status != 'completed':
            logger.warning(f"无法处理作文统计，ID: {essay_id}，状态不正确")
            return
        
        # 解析分数和错误数据
        scores = json.loads(essay.scores) if essay.scores else {}
        errors = json.loads(essay.errors) if essay.errors else []
        
        # 计算错误统计
        error_counts = {
            'spelling': 0,
            'grammar': 0,
            'punctuation': 0,
            'word_choice': 0,
            'structure': 0
        }
        
        for error in errors:
            error_type = error.get('type', 'other')
            if error_type in error_counts:
                error_counts[error_type] += 1
        
        # 计算文本分析指标
        text_analytics = TextAnalyzer(essay.original_text)
        readability = text_analytics.calculate_readability()
        lexical_diversity = text_analytics.calculate_lexical_diversity()
        syntactic_complexity = text_analytics.calculate_syntactic_complexity()
        
        # 创建或更新统计记录
        stats = EssayStatistics.query.filter_by(essay_id=essay_id).first()
        if not stats:
            stats = EssayStatistics(
                essay_id=essay_id,
                user_id=essay.user_id
            )
        
        # 更新统计数据
        stats.word_count = text_analytics.word_count
        stats.unique_word_count = text_analytics.unique_word_count
        stats.sentence_count = text_analytics.sentence_count
        stats.avg_sentence_length = text_analytics.avg_sentence_length
        
        stats.spelling_errors = error_counts['spelling']
        stats.grammar_errors = error_counts['grammar']
        stats.punctuation_errors = error_counts['punctuation']
        stats.word_choice_errors = error_counts['word_choice']
        stats.structure_errors = error_counts['structure']
        
        stats.content_score = scores.get('content', 0)
        stats.organization_score = scores.get('organization', 0)
        stats.language_score = scores.get('language', 0)
        stats.overall_score = scores.get('overall', 0)
        
        stats.readability_score = readability
        stats.lexical_diversity = lexical_diversity
        stats.syntactic_complexity = syntactic_complexity
        
        # 保存到数据库
        db.session.add(stats)
        db.session.commit()
        
        logger.info(f"成功处理作文统计数据，ID: {essay_id}")
        
        # 可选：更新用户进度跟踪
        update_user_progress.delay(essay.user_id)
        
        return {
            'status': 'success',
            'message': f'作文ID {essay_id} 的统计数据已处理'
        }
    
    except Exception as e:
        logger.error(f"处理作文统计数据失败，ID: {essay_id}: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }
```

## 7. 文本分析工具

```python
class TextAnalyzer:
    """文本分析工具类"""
    
    def __init__(self, text):
        self.text = text
        self.words = self._tokenize_words()
        self.sentences = self._tokenize_sentences()
        self.word_count = len(self.words)
        self.unique_word_count = len(set(self.words))
        self.sentence_count = len(self.sentences)
        self.avg_sentence_length = self.word_count / self.sentence_count if self.sentence_count > 0 else 0
    
    def _tokenize_words(self):
        """分词处理"""
        # 实现详细代码...
        return []
    
    def _tokenize_sentences(self):
        """分句处理"""
        # 实现详细代码...
        return []
    
    def calculate_readability(self):
        """计算可读性分数"""
        # 实现详细代码...
        return 0
    
    def calculate_lexical_diversity(self):
        """计算词汇多样性"""
        if self.word_count == 0:
            return 0
        return self.unique_word_count / self.word_count
    
    def calculate_syntactic_complexity(self):
        """计算句法复杂度"""
        # 实现详细代码...
        return 0
```

## 8. 数据可视化组件

### 8.1 进步报告组件

前端实现进步报告可视化组件，包括：
- 分数趋势图
- 错误减少曲线图
- 能力雷达图
- 进步摘要卡片

### 8.2 错误分布组件

错误分布可视化组件，包括：
- 错误类型饼图
- 错误频率柱状图
- 错误随时间变化折线图

## 9. 数据导出功能

```python
@analysis_bp.route('/export', methods=['GET'])
@login_required
def export_analysis_data():
    """导出分析数据"""
    # 获取导出类型
    export_type = request.args.get('type', 'csv')
    # 获取时间范围
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # 处理时间范围...
    # 获取数据...
    
    if export_type == 'csv':
        # 生成CSV文件
        csv_data = StringIO()
        writer = csv.writer(csv_data)
        
        # 写入表头
        writer.writerow(['日期', '作文ID', '标题', '总分', '内容得分', '组织得分', '语言得分', 
                       '拼写错误', '语法错误', '标点错误', '词语选择错误', '结构错误'])
        
        # 写入数据行
        for stat in stats:
            essay = Essay.query.get(stat.essay_id)
            writer.writerow([
                essay.submission_time.strftime('%Y-%m-%d'),
                essay.id,
                essay.title,
                stat.overall_score,
                stat.content_score,
                stat.organization_score,
                stat.language_score,
                stat.spelling_errors,
                stat.grammar_errors,
                stat.punctuation_errors,
                stat.word_choice_errors,
                stat.structure_errors
            ])
        
        # 创建响应
        response = make_response(csv_data.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=essay_analysis_{start_date}_to_{end_date}.csv'
        
        return response
    else:
        return jsonify({
            'status': 'error',
            'message': f'不支持的导出类型: {export_type}'
        }), 400
```

## 10. 智能学习建议

系统能够基于用户历史数据自动生成个性化学习建议，包括：
- 针对性的错误改进提示
- 学习资源推荐
- 能力提升练习建议

这些建议可在用户界面的"学习计划"部分呈现。 