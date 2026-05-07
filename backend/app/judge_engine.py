"""
代码评测引擎
支持 C/C++, Python, Java 代码的编译和运行
"""
import os
import subprocess
import tempfile
import time
import psutil
import shutil
from typing import Tuple, Optional
from pathlib import Path
from app.config import get_settings


class JudgeEngine:
    """代码评测引擎"""
    
    # 支持的语言
    SUPPORTED_LANGUAGES = ['c', 'cpp', 'python', 'java']
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        初始化评测引擎
        
        Args:
            temp_dir: 临时文件目录，如果不指定则使用配置或系统临时目录
        """
        self.settings = get_settings()
        
        # 设置临时目录
        if temp_dir:
            self.temp_dir = temp_dir
        elif self.settings.JUDGE_TEMP_DIR:
            self.temp_dir = self.settings.JUDGE_TEMP_DIR
        else:
            self.temp_dir = tempfile.gettempdir()
        
        # 从配置读取可执行文件路径
        self.python_executable = self.settings.PYTHON_EXECUTABLE
        self.gcc_executable = self.settings.GCC_EXECUTABLE
        self.gpp_executable = self.settings.GPP_EXECUTABLE
        self.javac_executable = self.settings.JAVAC_EXECUTABLE
        self.java_executable = self.settings.JAVA_EXECUTABLE
        
        # 默认超时和内存限制
        self.default_timeout = self.settings.JUDGE_DEFAULT_TIMEOUT
        self.default_memory_limit = self.settings.JUDGE_DEFAULT_MEMORY_LIMIT
        
    def judge(
        self,
        code: str,
        language: str,
        input_data: str,
        expected_output: str,
        time_limit: int = None,
        memory_limit: int = None
    ) -> Tuple[str, int, int, Optional[str], str]:
        """
        评测代码
        
        Args:
            code: 源代码
            language: 编程语言
            input_data: 输入数据
            expected_output: 期望输出
            time_limit: 时间限制（毫秒）
            memory_limit: 内存限制（MB）
            
        Returns:
            (status, time_used, memory_used, error_message, actual_output)
            status: accepted, wrong_answer, time_limit_exceeded, memory_limit_exceeded, 
                    runtime_error, compile_error
            time_used: 运行时间（毫秒）
            memory_used: 使用内存（KB）
            error_message: 错误信息
            actual_output: 实际输出
        """
        if language.lower() not in self.SUPPORTED_LANGUAGES:
            return 'compile_error', 0, 0, f'不支持的语言: {language}', ''
        
        time_limit_sec = (time_limit or self.default_timeout * 1000) / 1000
        memory_limit_mb = memory_limit or self.default_memory_limit
        
        try:
            # 编译代码（如果需要）
            if language.lower() in ['c', 'cpp', 'java']:
                compile_result = self._compile(code, language)
                if compile_result[0] != 'success':
                    # compile_result[1] contains an error message
                    return 'compile_error', 0, 0, compile_result[1], ''
                executable_path = compile_result[1]
            else:
                executable_path = None
            
            # 运行代码
            run_result = self._run(
                code, 
                language, 
                input_data, 
                executable_path,
                time_limit_sec,
                memory_limit_mb
            )
            
            status, output, time_used, memory_used, error_msg = run_result
            
            # 清理临时文件或目录（兼容可执行文件和 per-judge 目录）
            try:
                if executable_path:
                    if os.path.isdir(executable_path):
                        # Java per-judge 临时目录
                        shutil.rmtree(executable_path, ignore_errors=True)
                    else:
                        # C/C++ 可执行文件或其他单文件产物
                        if os.path.exists(executable_path):
                            try:
                                os.remove(executable_path)
                            except:
                                pass
                        # 删除可能的源文件（基于可执行路径前缀）
                        source_prefix = executable_path.rsplit('.', 1)[0]
                        for ext in ['.c', '.cpp', '.java', '.class', '.py']:
                            try:
                                if os.path.exists(source_prefix + ext):
                                    os.remove(source_prefix + ext)
                            except:
                                pass
            except:
                pass
            
            # 如果运行出错，直接返回
            if status != 'success':
                return status, time_used, memory_used, error_msg, output
            
            # 比较输出
            if self._compare_output(output, expected_output):
                return 'accepted', time_used, memory_used, None, output
            else:
                # 只返回简单的错误信息，不包含具体的期望输出和实际输出
                return 'wrong_answer', time_used, memory_used, '实际输出和期望输出不符合', output
                
        except Exception as e:
            return 'runtime_error', 0, 0, str(e), ''
    
    def _compile(self, code: str, language: str) -> Tuple[str, str]:
        """
        编译代码
        
        Returns:
            (status, executable_path_or_error_message)
        """
        # 创建临时源文件
        timestamp = int(time.time() * 1000)
        
        compile_cwd = self.temp_dir
        if language.lower() == 'c':
            source_file = os.path.join(self.temp_dir, f'temp_{timestamp}.c')
            executable = os.path.join(self.temp_dir, f'temp_{timestamp}.exe')
            compile_cmd = [self.gcc_executable, source_file, '-o', executable, '-O2']
        elif language.lower() == 'cpp':
            source_file = os.path.join(self.temp_dir, f'temp_{timestamp}.cpp')
            executable = os.path.join(self.temp_dir, f'temp_{timestamp}.exe')
            compile_cmd = [self.gpp_executable, source_file, '-o', executable, '-O2', '-std=c++17']
        elif language.lower() == 'java':
            # 为每次评测创建独立子目录，避免并发时 Main.class 冲突
            per_judge_dir = tempfile.mkdtemp(dir=self.temp_dir, prefix=f'judge_{timestamp}_')
            compile_cwd = per_judge_dir
            source_filename = 'Main.java'
            source_file = os.path.join(per_judge_dir, source_filename)
            # 使用相对文件名在指定 cwd 中调用 javac，避免路径解析差异
            compile_cmd = [self.javac_executable, source_filename]
            executable = per_judge_dir  # 返回目录路径，运行时使用 java -cp <dir> Main
        else:
            return 'compile_error', f'不支持的编译语言: {language}'
        
        # 写入源代码
        try:
            with open(source_file, 'w', encoding='utf-8') as f:
                f.write(code)
        except Exception as e:
            return 'error', f'写入源文件失败: {str(e)}'
        
        # 编译
        try:
            result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=compile_cwd
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                # 清理源文件或临时目录（如果为 java）
                try:
                    if language.lower() == 'java' and os.path.isdir(compile_cwd):
                        shutil.rmtree(compile_cwd, ignore_errors=True)
                    else:
                        if os.path.exists(source_file):
                            os.remove(source_file)
                except:
                    pass
                # 返回包含 cwd 和命令的详细信息，便于排查 javac 未被正确调用的问题
                cmd_str = ' '.join(compile_cmd)
                return 'compile_error', f'编译错误 (cwd={compile_cwd}, cmd="{cmd_str}"):\n{error_msg}'

            # 编译成功，但需要额外检查目标文件是否存在（避免极端情况下编译器未产生输出）
            if language.lower() in ['c', 'cpp']:
                if not os.path.exists(executable):
                    try:
                        os.remove(source_file)
                    except:
                        pass
                    return 'compile_error', '编译后未生成可执行文件'
            elif language.lower() == 'java':
                # 检查 Main.class 是否存在于 per-judge 目录
                class_file = os.path.join(compile_cwd, 'Main.class')
                if not os.path.exists(class_file):
                    try:
                        if os.path.isdir(compile_cwd):
                            shutil.rmtree(compile_cwd, ignore_errors=True)
                        else:
                            if os.path.exists(source_file):
                                os.remove(source_file)
                    except:
                        pass
                    return 'compile_error', f'编译后未生成 class 文件 (cwd={compile_cwd})'

            return 'success', executable
            
        except subprocess.TimeoutExpired:
            return 'error', '编译超时'
        except Exception as e:
            return 'error', f'编译异常: {str(e)}'
    
    def _run(
        self,
        code: str,
        language: str,
        input_data: str,
        executable_path: Optional[str],
        time_limit: float,
        memory_limit: int
    ) -> Tuple[str, str, int, int, Optional[str]]:
        """
        运行代码
        
        Returns:
            (status, output, time_used_ms, memory_used_kb, error_message)
        """
        try:
            # 准备运行命令
            if language.lower() == 'python':
                # Python 直接运行
                timestamp = int(time.time() * 1000)
                source_file = os.path.join(self.temp_dir, f'temp_{timestamp}.py')
                with open(source_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                run_cmd = [self.python_executable, source_file]
            elif language.lower() in ['c', 'cpp']:
                # 可执行文件应该存在
                if not executable_path or not os.path.exists(executable_path):
                    return 'runtime_error', '', 0, 0, '运行时错误: 未找到可执行文件'
                run_cmd = [executable_path]
            elif language.lower() == 'java':
                # Java 运行需要指定类名，使用 compile 返回的 per-judge 目录作为 classpath
                # 检查 per-judge 目录和 Main.class
                if not executable_path or not os.path.isdir(executable_path):
                    return 'runtime_error', '', 0, 0, '运行时错误: Java 运行目录不存在'
                class_file = os.path.join(executable_path, 'Main.class')
                if not os.path.exists(class_file):
                    return 'runtime_error', '', 0, 0, '运行时错误: 未找到 Main.class，请检查编译是否成功'
                run_cmd = [self.java_executable, '-cp', executable_path, 'Main']
            else:
                return 'runtime_error', '', 0, 0, f'不支持的运行语言: {language}'
            
            # 记录开始时间
            start_time = time.time()
            
            # 运行程序
            # 运行时也应在对应目录执行（Java 使用 per-judge 目录）
            run_cwd = self.temp_dir if language.lower() != 'java' else executable_path
            process = subprocess.Popen(
                run_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=run_cwd
            )
            
            # 监控内存使用 - 使用线程持续监控
            max_memory = 0
            import threading
            monitoring = {'running': True}
            
            def monitor_memory():
                """在后台线程中持续监控内存使用"""
                try:
                    ps_process = psutil.Process(process.pid)
                    while monitoring['running']:
                        try:
                            if ps_process.is_running():
                                memory_info = ps_process.memory_info()
                                current_memory = memory_info.rss // 1024  # 转换为 KB
                                nonlocal max_memory
                                max_memory = max(max_memory, current_memory)
                            else:
                                break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            break
                        time.sleep(0.01)  # 每10ms检查一次
                except:
                    pass
            
            # 启动内存监控线程
            monitor_thread = threading.Thread(target=monitor_memory, daemon=True)
            monitor_thread.start()
            
            try:
                # 发送输入并等待结果
                output, error = process.communicate(
                    input=input_data,
                    timeout=time_limit
                )
            except subprocess.TimeoutExpired:
                process.kill()
                monitoring['running'] = False
                # 清理临时文件
                if language.lower() == 'python' and os.path.exists(source_file):
                    try:
                        os.remove(source_file)
                    except:
                        pass
                return 'time_limit_exceeded', '', int(time_limit * 1000), max_memory, '运行超时'
            finally:
                # 停止内存监控
                monitoring['running'] = False
                monitor_thread.join(timeout=0.5)
            
            # 计算运行时间（毫秒）
            time_used = int((time.time() - start_time) * 1000)
            
            # 清理临时文件
            if language.lower() == 'python' and os.path.exists(source_file):
                try:
                    os.remove(source_file)
                except:
                    pass
            
            # 检查内存限制
            if max_memory > memory_limit * 1024:  # memory_limit 是 MB
                return 'memory_limit_exceeded', '', time_used, max_memory, '内存超限'
            
            # 检查运行时错误
            if process.returncode != 0:
                # 若 stderr/错误信息存在，返回更详细的错误信息，并把 stdout 也作为实际输出返回
                err_msg = error or ''
                out = output.strip() if output else ''
                # 包含返回码/信号信息，帮助诊断 segmentation fault（通常没有 stderr）
                rc = process.returncode
                detailed = f'运行时错误:'
                if err_msg:
                    detailed += f"\n{err_msg}"
                # 添加返回码信息
                try:
                    import signal as _signal
                    if rc < 0:
                        sig = -rc
                        try:
                            sig_name = _signal.Signals(sig).name
                        except Exception:
                            sig_name = str(sig)
                        detailed += f"\n进程被信号终止: {sig} ({sig_name})"
                    else:
                        detailed += f"\n返回码: {rc}"
                except Exception:
                    detailed += f"\n返回码: {rc}"

                if out:
                    detailed += f"\nstdout:\n{out}"
                return 'runtime_error', out, time_used, max_memory, detailed
            
            return 'success', output.strip(), time_used, max_memory, None
            
        except Exception as e:
            return 'runtime_error', '', 0, 0, f'运行异常: {str(e)}'
    
    def _compare_output(self, actual: str, expected: str) -> bool:
        """
        比较输出结果
        忽略行尾空白和文件尾换行
        
        Args:
            actual: 实际输出
            expected: 期望输出
            
        Returns:
            是否匹配
        """
        # 分行并去除每行尾部空白
        actual_lines = [line.rstrip() for line in actual.splitlines()]
        expected_lines = [line.rstrip() for line in expected.splitlines()]
        
        # 去除空行
        actual_lines = [line for line in actual_lines if line]
        expected_lines = [line for line in expected_lines if line]
        
        return actual_lines == expected_lines
