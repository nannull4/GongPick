

"""
현재 폴더에 있는 모든 PDF 파일에서 테이블을 추출하여,
각 페이지별로 별도의 CSV 파일을 생성하는 스크립트입니다.
tabula-py 라이브러리를 사용합니다.

필요한 라이브러리 설치:
pip install tabula-py pandas PyMuPDF

주의: 이 스크립트를 실행하려면 컴퓨터에 Java가 설치되어 있어야 합니다.
"""

import os
import pandas as pd
import fitz  # PyMuPDF
import traceback

def convert_pdf_to_csvs_by_page(pdf_path: str, output_dir: str = "output_csvs"):
    """
    하나의 PDF 파일에서 페이지별로 테이블을 추출하여 각각 별도의 CSV 파일로 저장합니다.

    :param pdf_path: 처리할 PDF 파일의 경로
    :param output_dir: 생성된 CSV 파일을 저장할 디렉터리
    """
    print(f"\n📄 '{pdf_path}' 파일 처리 시작...")

    try:
        import tabula

        # PyMuPDF(fitz)를 사용하여 PDF의 총 페이지 수를 가져옵니다.
        try:
            doc = fitz.open(pdf_path)
            total_pages = doc.page_count
            doc.close()
        except Exception as e:
            print(f"  ❌ PDF 파일 페이지 수를 읽는 중 오류 발생: {e}")
            print("     파일이 손상되었거나 암호화되었을 수 있습니다.")
            return
            
        print(f"  총 {total_pages} 페이지를 처리합니다.")

        # 각 페이지를 순회하며 테이블 추출
        for page_num in range(1, total_pages + 1):
            print(f"  - 페이지 {page_num} 처리 중...")
            
            # 현재 페이지만 타겟으로 하여 테이블 추출
            # stream=True는 격자선 없는 테이블, guess=False는 자동 추측 비활성화
            list_of_dfs = tabula.read_pdf(
                pdf_path, 
                pages=page_num, 
                multiple_tables=True, 
                stream=True, 
                guess=False
            )

            if not list_of_dfs:
                print(f"    - 페이지 {page_num}에서 테이블을 찾을 수 없습니다.")
                continue

            # 해당 페이지의 모든 테이블을 하나로 합침
            page_df = pd.concat([df for df in list_of_dfs if not df.empty], ignore_index=True)

            if page_df.empty:
                print(f"    - 페이지 {page_num}에서 유효한 데이터를 찾지 못했습니다.")
                continue
                
            # 불필요한 빈 행과 열을 제거하여 데이터 정리
            page_df.dropna(axis='columns', how='all', inplace=True)
            page_df.dropna(axis='rows', how='all', inplace=True)

            if page_df.empty:
                print(f"    - 페이지 {page_num}에서 데이터 정리 후 남은 내용이 없습니다.")
                continue

            # 저장할 파일명을 만듭니다. (예: 'my_document_page_1.csv')
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            output_filename = f"{base_name}_page_{page_num}.csv"
            output_filepath = os.path.join(output_dir, output_filename)

            # 정리된 DataFrame을 CSV 파일로 저장합니다.
            page_df.to_csv(output_filepath, index=False, encoding='utf-8-sig')

            print(f"    ✅ 성공! '{output_filename}' 파일로 저장되었습니다.")
            print(f"       (총 {len(page_df)}행, {len(page_df.columns)}열)")

    except ImportError:
        print("  ❌ 오류: 필요한 라이브러리가 설치되지 않았습니다.")
        print("     터미널에서 `pip install tabula-py pandas PyMuPDF` 명령어를 실행해주세요.")
    except Exception as e:
        print(f"  ❌ '{pdf_path}' 처리 중 오류 발생: {e}")
        if "java" in str(e).lower():
            print("     오류 메시지에 'java'가 포함되어 있습니다. 컴퓨터에 Java가 설치되어 있는지 확인해주세요.")
        # traceback.print_exc() # 더 자세한 오류를 보려면 이 줄의 주석을 해제하세요.

if __name__ == '__main__':
    # 결과를 저장할 폴더 이름
    output_directory = "output_csvs"

    # 현재 폴더에서 .pdf로 끝나는 모든 파일을 찾습니다.
    pdf_files = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]

    if not pdf_files:
        print("현재 폴더에 PDF 파일이 없습니다. 스크립트를 PDF 파일이 있는 폴더로 옮겨주세요.")
    else:
        print(f"총 {len(pdf_files)}개의 PDF 파일을 찾았습니다. 변환을 시작합니다.")
        
        # 출력 디렉토리가 없으면 생성합니다.
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
            print(f"📁 '{output_directory}' 폴더를 생성했습니다.")
        
        # 찾은 모든 PDF 파일에 대해 변환 함수를 실행합니다..
        for pdf_file in pdf_files:
            convert_pdf_to_csvs_by_page(pdf_file, output_directory)
        
        print("\n🎉 모든 작업이 완료되었습니다!")
