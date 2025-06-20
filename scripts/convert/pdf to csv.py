import os
import pandas as pd
import fitz  # PyMuPDF
import traceback

def convert_pdf_to_csvs_by_page(pdf_path: str, output_dir: str):
    """
    하나의 PDF 파일에서 페이지별로 테이블을 추출하여 각각 별도의 CSV 파일로 저장합니다.

    :param pdf_path: 처리할 PDF 파일의 전체 경로
    :param output_dir: 생성된 CSV 파일을 저장할 디렉터리 경로
    """
    print(f"\n📄 '{pdf_path}' 파일 처리 시작...")

    try:
        import tabula

        try:
            doc = fitz.open(pdf_path)
            total_pages = doc.page_count
            doc.close()
        except Exception as e:
            print(f"  ❌ PDF 파일 페이지 수를 읽는 중 오류 발생: {e}")
            return
            
        print(f"  총 {total_pages} 페이지를 처리합니다.")

        for page_num in range(1, total_pages + 1):
            print(f"  - 페이지 {page_num} 처리 중...")
            
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

            page_df = pd.concat([df for df in list_of_dfs if not df.empty], ignore_index=True)
            page_df.dropna(axis='columns', how='all', inplace=True)
            page_df.dropna(axis='rows', how='all', inplace=True)

            if page_df.empty:
                print(f"    - 페이지 {page_num}에서 유효한 데이터가 없습니다.")
                continue

            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            output_filename = f"{base_name}_page_{page_num}.csv"
            output_filepath = os.path.join(output_dir, output_filename)

            page_df.to_csv(output_filepath, index=False, encoding='utf-8-sig')

            print(f"    ✅ 저장 완료: {output_filename} (행: {len(page_df)}, 열: {len(page_df.columns)})")

    except ImportError:
        print("필요한 라이브러리가 설치되지 않았습니다. pip install tabula-py pandas PyMuPDF")
    except Exception as e:
        print(f"  ❌ 에러 발생: {e}")
        if "java" in str(e).lower():
            print("Java 설치 여부를 확인해주세요.")

if __name__ == '__main__':
    input_directory = os.path.abspath("../../data/raw")
    output_directory = os.path.abspath("../../data/processed")

    # PDF 목록 가져오기
    pdf_files = [f for f in os.listdir(input_directory) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print("📂 raw 폴더에 PDF가 없습니다.")
    else:
        print(f"총 {len(pdf_files)}개의 PDF 파일을 찾았습니다.")

        os.makedirs(output_directory, exist_ok=True)

        for pdf_file in pdf_files:
            pdf_path = os.path.join(input_directory, pdf_file)
            convert_pdf_to_csvs_by_page(pdf_path, output_directory)

        print("\n🎉 모든 변환 작업이 완료되었습니다!")
